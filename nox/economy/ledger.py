class IntelligenceLedger:

    def __init__(self):
        self.balances = {}

    def create_account(self, owner_id):

        if owner_id not in self.balances:
            self.balances[owner_id] = 1000   # Starting credits

    def get_balance(self, owner_id):
        return self.balances.get(owner_id, 0)

    def deduct(self, owner_id, cost):

        if self.get_balance(owner_id) >= cost:
            self.balances[owner_id] -= cost
            return True

        return False