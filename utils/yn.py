def prompt_yes_no(msg: str) -> bool:
    while True:
        response = input(f"{msg} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'.")