def format_simulation_for_llm(simulation_output):
    before = simulation_output["before"]
    after = simulation_output["after"]

    return (
        "Supply chain disruption analysis:\n"
        f"- Disruption type: {simulation_output['disruption_type']}\n"
        f"- Baseline duration (seconds): {before['duration_seconds']}\n"
        f"- Simulated duration (seconds): {after['duration_seconds']}\n"
        f"- Baseline cost: {before['estimated_cost']}\n"
        f"- Simulated cost: {after['estimated_cost']}\n"
        f"- Risk transition: {simulation_output['risk_change']}\n"
        f"- Delay percentage: {simulation_output['delay_percentage']}%\n"
        f"- Cost increase percentage: {simulation_output['cost_increase_percentage']}%\n"
        f"- Baseline recommendation: {before['risk']['recommendation']}\n"
        f"- Simulated recommendation: {after['risk']['recommendation']}\n"
        "Generate mitigation options, preferred transport alternatives, and executive-ready action items."
    )
