from investment_terminal.cli.grounded_ai_live import _print_human


def report(*, retry_delays=None):
    operation = {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }
    if retry_delays is not None:
        operation["retry_delay_seconds"] = retry_delays

    return {
        "trace": {
            "request_id": "r1",
            "provider_identity": "OPENAI",
            "model_identity": "gpt-test",
            "provider_operation": operation,
            "validation_status": "ADMISSIBLE",
            "selected_knowledge_identities": [],
            "claim_count": 1,
            "citation_count": 1,
        },
        "generation": {
            "answer": {
                "claims": [
                    {
                        "text": "x",
                        "citations": [
                            {
                                "knowledge_identity": "K@1",
                                "provenance_status": "COMPLETE",
                            }
                        ],
                    }
                ]
            }
        },
    }


def test_human_output_shows_applied_retry_delays(capsys) -> None:
    _print_human(
        report(
            retry_delays=["1", "5.5"]
        )
    )

    output = capsys.readouterr().out
    assert "Retry Delays : 1, 5.5 s" in output


def test_human_output_omits_retry_delay_line_when_absent(capsys) -> None:
    _print_human(
        report()
    )

    output = capsys.readouterr().out
    assert "Retry Delays" not in output


def test_human_output_omits_retry_delay_line_for_empty_sequence(capsys) -> None:
    _print_human(
        report(
            retry_delays=[]
        )
    )

    output = capsys.readouterr().out
    assert "Retry Delays" not in output
