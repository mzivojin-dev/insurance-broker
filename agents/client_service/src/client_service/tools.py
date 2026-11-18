import json
import os

import boto3

from agent_core import Transcript, tool


def make_local_tools(transcript: Transcript, client_id: str):
    @tool
    def cite(source_doc: str) -> str:
        """Record a clause you used in the answer. Call once per clause, before answering."""
        transcript.citations.append(source_doc)
        return "cited"

    @tool
    def escalate_to_csr(summary: str, reason: str, clauses: list[str] | None = None) -> str:
        """Hand the conversation to a human CSR. Use for cancellations, coverage interpretation,
        claim disputes, complaints, or when no clause answers the question."""
        msg = {"client_id": client_id, "summary": summary, "reason": reason, "clauses": clauses or []}
        if os.environ.get("ESCALATION_QUEUE_URL"):
            boto3.client("sqs").send_message(QueueUrl=os.environ["ESCALATION_QUEUE_URL"],
                                             MessageBody=json.dumps(msg))
        return "A licensed account manager will contact the client within one business day."

    return [cite, escalate_to_csr]