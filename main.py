import pickle
from collections import UserDict
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple


def input_error(func: Callable[..., str]) -> Callable[..., str]:
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e)
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Not enough arguments for this command."
        except TypeError:
            return "Invalid arguments."
    return wrapper


class Field:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    def __init__(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty.")
        super().__init__(value.strip())


class Phone(Field):
    def __init__(self, value: str) -> None:
        cleaned = value.strip()
        if not (cleaned.isdigit() and len(cleaned) == 10):
            raise ValueError("Invalid phone number. Phone must contain exactly 10 digits.")
        super().__init__(cleaned)


class Birthday(Field):
    def __init__(self, value: str) -> None:
        try:
            birthday_date = datetime.strptime(value.strip(), "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(birthday_date)

    @property
    def date(self) -> date:
        return self.value


class Record:
    def __init__(self, name: str) -> None:
        self.name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Optional[Birthday] = None

    def add_phone(self, phone: str) -> None:
        self.phones.append(Phone(phone))

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        for i, phone in enumerate(self.phones):
            if phone.value == old_phone:
                self.phones[i] = Phone(new_phone)
                return
        raise ValueError("Old phone number not found.")

    def add_birthday(self, birthday: str) -> None:
        self.birthday = Birthday(birthday)

    def show_birthday(self) -> str:
        if self.birthday is None:
            return "Birthday is not set."
        return self.birthday.date.strftime("%d.%m.%Y")

    def __str__(self) -> str:
        phones_str = ", ".join(phone.value for phone in self.phones) if self.phones else "—"
        birthday_str = self.show_birthday() if self.birthday else "—"
        return f"{self.name.value}: phones [{phones_str}], birthday [{birthday_str}]"


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        return self.data.get(name)

    def get_upcoming_birthdays(self) -> List[Dict[str, str]]:
        today = date.today()
        upcoming_birthdays = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday = record.birthday.date
            try:
                birthday_this_year = birthday.replace(year=today.year)
            except ValueError:
                birthday_this_year = date(today.year, 2, 28)

            if birthday_this_year < today:
                try:
                    birthday_this_year = birthday_this_year.replace(year=today.year + 1)
                except ValueError:
                    birthday_this_year = date(today.year + 1, 2, 28)

            days_diff = (birthday_this_year - today).days

            if 0 <= days_diff <= 7:
                congratulation_date = birthday_this_year
                if congratulation_date.weekday() == 5:
                    congratulation_date += timedelta(days=2)
                elif congratulation_date.weekday() == 6:
                    congratulation_date += timedelta(days=1)

                upcoming_birthdays.append(
                    {
                        "name": record.name.value,
                        "congratulation_date": congratulation_date.strftime("%Y.%m.%d"),
                    }
                )

        return upcoming_birthdays


def save_data(book: AddressBook, filename: str = "addressbook.pkl") -> None:
    with open(filename, "wb") as file:
        pickle.dump(book, file)


def load_data(filename: str = "addressbook.pkl") -> AddressBook:
    try:
        with open(filename, "rb") as file:
            return pickle.load(file)
    except FileNotFoundError:
        return AddressBook()


def parse_input(user_input: str) -> Tuple[str, List[str]]:
    parts = user_input.strip().split()
    if not parts:
        return "", []
    command = parts[0].lower()
    args = parts[1:]
    return command, args


@input_error
def add_contact(args: List[str], book: AddressBook) -> str:
    name, phone = args
    record = book.find(name)

    if record is None:
        record = Record(name)
        record.add_phone(phone)
        book.add_record(record)
        return "Contact added."
    else:
        record.add_phone(phone)
        return "Contact updated."


@input_error
def change_contact(args: List[str], book: AddressBook) -> str:
    name, old_phone, new_phone = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Phone number changed."


@input_error
def show_phone(args: List[str], book: AddressBook) -> str:
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return "No phones saved for this contact."
    return ", ".join(phone.value for phone in record.phones)


@input_error
def show_all(book: AddressBook) -> str:
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args: List[str], book: AddressBook) -> str:
    name, birthday = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args: List[str], book: AddressBook) -> str:
    name = args[0]
    record = book.find(name)
    if record is None:
        raise KeyError
    return record.show_birthday()


@input_error
def birthdays(book: AddressBook) -> str:
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    return "\n".join(
        f'{item["name"]}: {item["congratulation_date"]}' for item in upcoming
    )


def main() -> None:
    book = load_data()
    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            save_data(book)
            print("Good bye!")
            break
        elif command == "":
            print("Please enter a command.")
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(book))
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()







    