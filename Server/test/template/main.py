from models import User, Admin
from utils import format_greeting

def main():
    u = User("Alice")
    a = Admin("Bob")
    
    greeting = format_greeting(u.get_name())
    print(greeting)
    
    print(a.get_privileges())

if __name__ == "__main__":
    main()
