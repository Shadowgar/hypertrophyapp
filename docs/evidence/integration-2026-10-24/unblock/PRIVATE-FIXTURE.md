# Exact private Phase 1 CI fixture proposal

The owner-authorized Drive copy was downloaded as raw XLSX bytes. Before parsing,
SHA-256 matched `46f50999771cbb454b325729b2d2a77515dbcf2cdd86891e4543eab65019bb71`
(88,063 bytes). Both original source-fidelity tests pass unchanged locally.
No workbook content, encoded payload, download URL or credentials belong in Git,
public logs, caches, images or artifacts. Drive is not a runtime dependency.

## Proposed channel and boundary

Use GitHub Actions' existing encrypted **environment secrets**, not a new storage
service or access credential. The `licensed-phase1-fixture` environment must be
configured with an owner required reviewer **before any fixture secrets are set**.
Only a reviewed exact candidate may receive the three `PHASE1_SOURCE_B64_1..3`
payload chunks. Each is at most 40,000 base64 characters (under GitHub's 48 KB
secret limit); concatenating and decoding returns the original bytes exactly.
These are private source payloads, not authentication tokens. Do not auto-approve
the environment, permit untrusted PR code, use `pull_request_target`, or assume
fork/Dependabot jobs can access them. A workflow conditional alone cannot protect
repository secrets from modified same-repository workflow code.

The API job waits for environment review. The materializer validates length and
historical SHA before exclusive creation of the ignored fixture at mode 0600 in
a mode-0700 directory. It removes source environment variables before tests,
preserves every pytest argument and exit status, captures raw output/JUnit only in
runner-private temporary storage, emits counts and safe failure identifiers, and
removes the fixture afterwards. An always-step handles ordinary interrupted-job
cleanup. Hosted runners are ephemeral; no artifact/cache/upload step is added.
The private output capture matters because unchanged source assertions can print
workbook cell contents on failure. Test bodies and expectations are not weakened.
The fixture and qualification directories are excluded from Docker build contexts.

## Qualification and activation

Local tests cover exact-byte reconstruction, permissions, missing/corrupt/wrong
source, refusal to overwrite files or follow symlinks, and non-disclosing failure
summaries. A separate isolated checkout runs the two original unchanged tests
through the same materializer with the privately verified real bytes.

Provisioning the protected environment and copying the private payload require
owner authorization for this specific channel. Without it, no payload is uploaded;
a failing or waiting API check remains incomplete, not waived. Once authorized,
verify environment protection through the provider, set chunks without printing
them, approve only the intended head, and verify the full API job's actual result.
No deployment or production operation is involved.

Provider documentation: [secret size and availability](https://docs.github.com/en/actions/reference/security/secrets),
[environment protection and secret access](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments).
