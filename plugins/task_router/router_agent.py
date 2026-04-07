


class RouterAgent:

    def __init__(self, capability_index):

        self.index = capability_index

    def route(self, capability):

        result = self.index.search(capability)

        if not result:
            return None

        print(
            f"[router] matched capability {result['capability']} → plugin {result['plugin']}"
        )

        return result["plugin"]