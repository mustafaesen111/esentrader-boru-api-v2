# Copy Engine iskeleti
# TradingView master emirlerinden follower hesaplara dağıtım burada yapılacak

class CopyEngine:
    def __init__(self):
        self.followers = []

    def add_follower(self, follower):
        self.followers.append(follower)

    def distribute(self, master_order):
        # ileride oransal dağıtım burada yapılacak
        return {
            "distributed_to": len(self.followers),
            "master_order": master_order
        }
