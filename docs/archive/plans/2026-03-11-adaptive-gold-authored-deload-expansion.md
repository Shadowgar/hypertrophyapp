# Adaptive Gold Authored Deload Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend adaptive-gold from authored week 2 into a real authored mesocycle with week 3 progression and week 4 deload doctrine.

**Architecture:** Preserve authored week variants at the loader boundary, add explicit authored week role metadata, and let scheduler select the authored week from `prior_generated_weeks` before applying compression, capping, substitutions, and deload modifiers. Treat authored deload as a first-class mesocycle signal rather than a side effect inferred from heuristics.

**Tech Stack:** FastAPI API tests, Python scheduler/loader runtime, Pydantic adaptive/template schemas, pytest with SQLite temp DBs.
