"""
Tests for machine deployment decisions.
"""

from investment_terminal.review.deployment_decision_service import (
    DeploymentDecisionService,
)


def freshness(
    *,
    all_ready: bool = True,
) -> dict:
    return {
        "status": "CONNECTED",
        "source": {
            "all_ready": all_ready,
        },
    }


def recommendations(
    labels: list[str],
) -> dict:
    return {
        "status": "CONNECTED",
        "recommendations": {
            "items": [
                {
                    "symbol": f"S{index}",
                    "recommendation": label,
                }
                for index, label in enumerate(
                    labels,
                    start=1,
                )
            ]
        },
    }


def test_waits_when_data_is_not_ready() -> None:
    result = DeploymentDecisionService().decide(
        data_freshness=freshness(
            all_ready=False,
        ),
        machine_recommendations=recommendations(
            [
                "BUY",
                "BUY",
            ]
        ),
    )

    assert result.mode == "WAIT"
    assert result.deployment_fraction == 0.0
    assert result.confidence == "LOW"


def test_uses_partial_deployment_for_moderate_breadth() -> None:
    result = DeploymentDecisionService().decide(
        data_freshness=freshness(),
        machine_recommendations=recommendations(
            [
                "BUY",
                "ACCUMULATE",
                "WATCH",
                "HOLD",
                "WATCH",
                "WATCH",
            ]
        ),
    )

    assert result.mode == "PARTIAL_DEPLOYMENT"
    assert result.deployment_fraction == 0.25
    assert result.positive_count == 2
    assert result.positive_breadth == round(
        2 / 6,
        8,
    )


def test_caps_strong_signal_at_half_deployment() -> None:
    result = DeploymentDecisionService().decide(
        data_freshness=freshness(),
        machine_recommendations=recommendations(
            [
                "BUY",
                "BUY",
                "ACCUMULATE",
                "WATCH",
                "HOLD",
            ]
        ),
    )

    assert result.mode == "PARTIAL_DEPLOYMENT"
    assert result.deployment_fraction == 0.50
    assert result.confidence == "HIGH"
    assert result.external_context_required is True


def test_waits_for_weak_breadth() -> None:
    result = DeploymentDecisionService().decide(
        data_freshness=freshness(),
        machine_recommendations=recommendations(
            [
                "BUY",
                "WATCH",
                "WATCH",
                "HOLD",
                "AVOID",
            ]
        ),
    )

    assert result.mode == "WAIT"
    assert result.deployment_fraction == 0.0


def test_result_is_json_ready() -> None:
    payload = DeploymentDecisionService().decide(
        data_freshness=freshness(),
        machine_recommendations=recommendations(
            [
                "BUY",
                "ACCUMULATE",
                "WATCH",
                "HOLD",
            ]
        ),
    ).to_dict()

    assert payload["mode"] == "PARTIAL_DEPLOYMENT"
    assert payload["deployment_percent"] == 50.0
    assert payload["external_context_required"] is True