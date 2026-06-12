class User:
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

class Admin(User):
    def get_privileges(self):
        return ["read", "write", "delete"]
