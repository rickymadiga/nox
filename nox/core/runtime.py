from nox.core.capability_index import CapabilityIndex
from nox.core.message_bus import MessageBus
from nox.core.memory import AgentMemory


class Runtime:
    """Manages agent registration, routing, and communication."""

    def __init__(self):
        """Initialize the runtime with core components."""
        # Agent storage
        self.registry = {}
        
        # Capability search/indexing
        self.capability_index = CapabilityIndex()
        
        # Shared memory across agents
        self.memory = AgentMemory()
        
        # Inter-agent communication
        self.bus = MessageBus()

    async def route(self, task):
        """Route a task to the appropriate agent.
        
        Args:
            task: The task to be routed to an agent.
            
        Returns:
            The result from the task router agent.
            
        Raises:
            RuntimeError: If the task router agent is not registered.
        """
        if "task_router" not in self.registry:
            raise RuntimeError("Task router agent not registered")
        
        router = self.registry["task_router"]
        result = await router.route(task)
        
        return result

    def register_agent(self, name, agent):
        """Register an agent and its capabilities.
        
        Args:
            name (str): The unique identifier for the agent.
            agent: The agent instance to register.
        """
        self.registry[name] = agent
        
        # Auto-register capabilities from agent docstring
        if hasattr(agent, "__doc__") and agent.__doc__:
            self.capability_index.register(name, agent.__doc__)
        
        print(f"[AGENT] {name} registered")

    def get_agent(self, name):
        """Retrieve a registered agent by name.
        
        Args:
            name (str): The agent identifier.
            
        Returns:
            The agent instance, or None if not found.
        """
        return self.registry.get(name)