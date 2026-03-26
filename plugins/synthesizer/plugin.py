from .agent import SynthesizerAgent


def register(runtime):

    agent = SynthesizerAgent(runtime)

    runtime.register_agent("synthesizer", agent)