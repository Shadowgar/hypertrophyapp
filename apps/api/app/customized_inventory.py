"""Account-owned location inventory; user facts never grant science-policy authority."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from core_engine.customized.audit import content_hash
from core_engine.customized.models import StrengthReport
from core_engine.customized.inventory import attainable_loads
from .models import TrainingEquipmentProfile

VERSION='customized-location-profile-v1'


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',hide_input_in_errors=True)


class WeightCount(Strict):
    weight:float=Field(gt=0,le=2000,allow_inf_nan=False,strict=True)
    count:int=Field(ge=1,le=128,strict=True)


class Stack(Strict):
    minimum:float=Field(gt=0,le=2000,allow_inf_nan=False,strict=True)
    maximum:float=Field(gt=0,le=2000,allow_inf_nan=False,strict=True)
    increment:float=Field(gt=0,le=2000,allow_inf_nan=False,strict=True)


class EquipmentSetup(Strict):
    key:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    label:str=Field(min_length=1,max_length=120)
    kind:Literal['dumbbell','barbell','machine_stack','bodyweight']
    unit:Literal['kg','lb']
    weights:list[WeightCount]=Field(default_factory=list,max_length=128)
    plates:list[WeightCount]=Field(default_factory=list,max_length=32)
    bar_weight:float|None=Field(default=None,gt=0,le=2000,allow_inf_nan=False,strict=True)
    stack:Stack|None=None
    min_load:float|None=Field(default=None,ge=0,le=2000,allow_inf_nan=False,strict=True)
    max_load:float|None=Field(default=None,gt=0,le=2000,allow_inf_nan=False,strict=True)
    setup_note:str=Field(min_length=1,max_length=500)

    def inventory(self):
        data=self.model_dump(mode='json',exclude_none=True)
        if self.stack is not None:
            if self.weights:raise ValueError('Declare machine stack labels or a ladder, not both')
            data.pop('weights',None)
        return data

    @model_validator(mode='after')
    def actual_loads(self):
        attainable_loads(self.inventory())
        return self


class StrengthInformation(Strict):
    report_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    variant_id:str=Field(min_length=1,max_length=96)
    setup_key:str=Field(min_length=1,max_length=64)
    kind:Literal['1rm','e1rm']
    load:float=Field(gt=0,le=2000,allow_inf_nan=False,strict=True)
    unit:Literal['kg','lb']
    observed_on:date
    confirmed:bool=Field(default=False,strict=True)
    method_reference:str|None=Field(default=None,min_length=1,max_length=240)
    setup_fingerprint:str|None=Field(default=None,max_length=64)


class LocationProfile(Strict):
    location_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    location_name:str=Field(min_length=1,max_length=120)
    equipment:list[str]=Field(max_length=32)
    unavailable_variants:list[str]=Field(default_factory=list,max_length=64)
    setups:list[EquipmentSetup]=Field(default_factory=list,max_length=64)
    assignments:dict[str,str]=Field(default_factory=dict,max_length=64)
    strength_reports:list[StrengthInformation]=Field(default_factory=list,max_length=32)

    @model_validator(mode='after')
    def references(self):
        from core_engine.customized.library import review_catalog
        catalog={e.variant_id:e for e in review_catalog().exercises}
        tags={tag for e in catalog.values() for tag in e.required_equipment}|{'barbell','rack','cable','bands'}
        if set(self.equipment)-tags or set(self.unavailable_variants)-catalog.keys():raise ValueError('Unknown equipment or variant')
        setups={s.key:s for s in self.setups}
        if len(setups)!=len(self.setups):raise ValueError('Duplicate setup identity')
        for variant,key in self.assignments.items():
            if variant not in catalog or key not in setups:raise ValueError('Unknown variant/setup assignment')
            expected={'dumbbell':'dumbbell','machine':'machine_stack','barbell':'barbell','bodyweight':'bodyweight'}[catalog[variant].load_identity.implement]
            if setups[key].kind!=expected:raise ValueError('Incompatible implement assignment')
        if len({r.report_id for r in self.strength_reports})!=len(self.strength_reports):raise ValueError('Duplicate strength report')
        for r in self.strength_reports:
            if self.assignments.get(r.variant_id)!=r.setup_key:raise ValueError('Strength report requires exact assigned variant/setup')
            if r.kind=='e1rm' and not r.method_reference:raise ValueError('An estimate requires its method/source')
        return self


class ProfileCommand(Strict):
    expected_revision:int=Field(ge=0,strict=True)
    profile:LocationProfile


def read_profile(db,subject):
    row=db.get(TrainingEquipmentProfile,subject)
    return dict(version=VERSION,revision=row.revision if row else 0,profile=row.data if row else None)


def catalog_for_profile(catalog,document):
    if not document or not document['profile']:return catalog
    profile=LocationProfile.model_validate(document['profile']);setups={s.key:s for s in profile.setups};exercises=[]
    for e in catalog.exercises:
        if e.variant_id in profile.unavailable_variants or not set(e.required_equipment)<=set(profile.equipment):continue
        key=profile.assignments.get(e.variant_id)
        if e.load_identity.basis=='bodyweight':exercises.append(e);continue
        if key is None:continue  # No unconfirmed physical setup masquerades as known equipment.
        setup=setups[key];count=2 if e.load_identity.basis=='per_hand' and e.variant_id!='db_supported_row' else 1
        weights=attainable_loads(setup.inventory(),required_count=count)
        if not weights:continue
        identity=replace(e.load_identity,unit='kg',equipment_key='location:'+content_hash((profile.location_id,key)),
            setup=e.load_identity.setup+'; '+setup.setup_note)
        exercises.append(replace(e,load_identity=identity,attainable_loads=weights))
    return replace(catalog,version='actual-inventory-v1:'+content_hash(document),exercises=tuple(exercises))


def strength_reports(document,catalog,as_of):
    if not document or not document['profile']:return ()
    exercises={e.variant_id:e for e in catalog.exercises};result=[]
    for r in LocationProfile.model_validate(document['profile']).strength_reports:
        if r.setup_fingerprint!=report_setup_fingerprint(document['profile'],r.model_dump()):continue
        e=exercises.get(r.variant_id)
        if e is None:continue
        factor=Decimal('0.45359237') if r.unit=='lb' else Decimal(1)
        result.append(StrengthReport(r.report_id,r.kind,e.load_identity,r.observed_on,float(Decimal(str(r.load))*factor),
            r.confirmed,'account_entered:'+r.report_id,r.method_reference))
    return tuple(result)


def report_setup_fingerprint(profile,report):
    setup=next((s for s in profile['setups'] if s['key']==report['setup_key']),None)
    return content_hash((profile['location_id'],report['variant_id'],
        {k:setup[k] for k in ('key','kind','unit','setup_note')} if setup else None))


def bind_report_setups(current,data):
    old={r['report_id']:r for r in (current['profile'] or {}).get('strength_reports',[])}
    for r in data['strength_reports']:
        fingerprint=report_setup_fingerprint(data,r)
        r['setup_fingerprint']=old[r['report_id']].get('setup_fingerprint') if r['report_id'] in old else fingerprint
        if r['setup_fingerprint']!=fingerprint:r['confirmed']=False
    return data


def inventory_issues(catalog,document):
    if not document or not document['profile']:return ['Save actual equipment and loads to qualify automatic calibration; none are assumed.']
    p=LocationProfile.model_validate(document['profile']);setups={s.key:s for s in p.setups};issues=[]
    for e in catalog.exercises:
        if not set(e.required_equipment)<=set(p.equipment):continue
        if e.variant_id in p.unavailable_variants:
            issues.append(e.name+': explicitly unavailable at this location.');continue
        if e.load_identity.basis=='bodyweight':continue
        setup=setups.get(p.assignments.get(e.variant_id))
        if setup is None:issues.append(e.name+': assign the actual equipment setup before it can be generated.');continue
        count=2 if e.load_identity.basis=='per_hand' and e.variant_id!='db_supported_row' else 1
        if not attainable_loads(setup.inventory(),required_count=count):
            issues.append(e.name+f': no attainable weight for {count} required implement(s) within your declared limits.')
    return issues
