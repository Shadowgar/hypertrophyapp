# Safe development context

Active navigation/safety procedure under [AGENTS.md](../../AGENTS.md), [scoped context](../context/CONTEXT_MANIFEST.yaml), [DB safety lock](../../DB_SAFETY_LOCK.md), [test strategy](../quality/test-strategy.md) and [plan registry](../plans/README.md).

Work on an isolated branch/worktree with the authorized package, controlling contracts and explicit test targets. Before imports, startup or DDL, verify the disposable database identity and cleared environment. A new container alone is not database isolation. Do not copy live env, DB files, personal data, logs or credentials into review artifacts. Protect original source licensing and runtime asset paths.

Run service/test/build/install/migration commands only within the authorized task scope and verified safe targets; production changes and deployment require explicit authorization. Historical root quickstart, [working-set reset instructions](../implementation/WORKING_SET.md), mini preflight and next-task outputs are not current approved safe procedures. The scripts still consume legacy paths and may select archived tasks; a separately authorized tooling update must migrate them to accepted bounded plans and enforce honest exits/isolated targets.

For authorized implementation record command/environment/result/artifacts under the [evidence policy](../evidence/README.md). Never infer permission from a checklist or silently repair production configuration. Deployment/restore/ingress procedures require effective-state knowledge and operator approval; documentation or historical commands alone do not supply that authorization.
