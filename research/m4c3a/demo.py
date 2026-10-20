"""Generate synthetic review HTML through the actual guarded app; no server/DB.

Must be invoked in an isolated environment with --synthetic-review. HTML goes to
stdout so the caller chooses a disposable artifact destination. No fixture or
policy is installed and no production app/startup is imported.
"""
import argparse
import sys

from fastapi.testclient import TestClient
from app.customized_preview_http import create_preview_app
from app.customized_preview_models import PreviewResponse
from app.customized_preview_view import render_comparison
from .fixtures import demo_request,demo_server,demo_principal,demo_context


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-review",action="store_true",help="Explicitly authorize synthetic nonprescriptive demonstration")
    args=parser.parse_args()
    if not args.synthetic_review:
        parser.error("Synthetic review is disabled; pass --synthetic-review explicitly")
    # In-process synthetic auth port: no live account, credential or service.
    async def fixture_principal(request):
        return demo_principal()
    responses=[]
    with TestClient(create_preview_app(server=demo_server(),authenticate=fixture_principal,
            context_port=lambda zone:demo_context())) as client:
        for request in (demo_request(),demo_request(short=True,accept_tradeoffs=True)):
            response=client.post("/customized/preview",json=request.model_dump(mode="json"))
            response.raise_for_status()
            responses.append(PreviewResponse.model_validate(response.json()))
    sys.stdout.write(render_comparison(tuple(responses)))


if __name__=="__main__":
    main()
