class EconomyGate:

    def __init__(self, ledger, cost_model):
        self.ledger = ledger
        self.cost_model = cost_model

    def allow_execution(self, user_id, task):

        cost = self.cost_model.estimate_intelligence_cost(task)

        return self.ledger.deduct(user_id, cost), cost