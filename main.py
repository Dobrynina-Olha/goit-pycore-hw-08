from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar


T = TypeVar("T")


def input_error(func: Callable[..., str]) -> Callable[..., str]:
    """
    Decorator that catches common input and value errors and returns user-friendly messages.
    """
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
    """
    Base class for contact fields.
    Stores a single value as a string or a domain-specific type.
    """

    def __init__(self, value: Any) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    """
    Contact name field.
    """

    def __init__(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Name cannot be empty.")
        super().__init__(value.strip())


class Phone(Field):
    """
    Phone field. Must contain exactly 10 digits.
    """

    def __init__(self, value: str) -> None:
        cleaned = value.strip()
        if not (cleaned.isdigit() and len(cleaned) == 10):
            raise ValueError("Invalid phone number. Phone must contain exactly 10 digits.")
        super().__init__(cleaned)


class Birthday(Field):
    """
    Birthday field. Accepts date in format DD.MM.YYYY and stores it as datetime.date.
    """

    def __init__(self, value: str) -> None:
        try:
            dt = datetime.strptime(value.strip(), "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(dt)

    @property
    def date(self) -> date:
        """
        Returns birthday as datetime.date.
        """
        if not isinstance(self.value, date):
            raise ValueError("Birthday value is corrupted.")
        return self.value


class Record:
    """
    A single address book record: name, list of phones, optional birthday.
    """

    def __init__(self, name: str) -> None:
        self.name: Name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Optional[Birthday] = None

    def add_phone(self, phone: str) -> None:
        """
        Adds a validated phone to the record.
        """
        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str) -> None:
        """
        Removes a phone by exact value match.
        """
        self.phones = [p for p in self.phones if p.value != phone]

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        """
        Replaces old_phone with new_phone if old_phone exists.
        """
        for idx, p in enumerate(self.phones):
            if p.value == old_phone:
                self.phones[idx] = Phone(new_phone)
                return
        raise ValueError("Old phone number not found.")

    def find_phone(self, phone: str) -> Optional[Phone]:
        """
        Finds and returns a Phone object by its value, or None.
        """
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday: str) -> None:
        """
        Adds (or overwrites) birthday in format DD.MM.YYYY.
        """
        self.birthday = Birthday(birthday)

    def show_birthday(self) -> str:
        """
        Returns birthday as string in DD.MM.YYYY, or a message if missing.
        """
        if self.birthday is None:
            return "Birthday is not set."
        return self.birthday.date.strftime("%d.%m.%Y")

    def __str__(self) -> str:
        phones_str = ", ".join(str(p) for p in self.phones) if self.phones else "—"
        bday_str = self.show_birthday() if self.birthday else "—"
        return f"{self.name.value}: phones [{phones_str}], birthday [{bday_str}]"


class AddressBook(UserDict):
    """
    Address book that maps contact name -> Record.
    """

    def add_record(self, record: Record) -> None:
        """
        Adds a Record to the book.
        """
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        """
        Finds a record by name. Returns Record or None.
        """
        return self.data.get(name)

    def delete(self, name: str) -> None:
        """
        Deletes a record by name.
        """
        if name not in self.data:
            raise KeyError
        del self.data[name]

    def get_upcoming_birthdays(self) -> List[Dict[str, str]]:
        """
        Returns a list of upcoming birthdays within next 7 days.
        If a birthday falls on weekend, congratulation date is moved to Monday.

        Output format:
        [{"name": "Bill", "congratulation_date": "2026.03.05"}, ...]
        """
        today = date.today()
        end_day = today + timedelta(days=7)

        result: List[Dict[str, str]] = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            bday = record.birthday.date
            # Next occurrence in this year
            try:
                next_bday = bday.replace(year=today.year)
            except ValueError:
                # For 29.02: if current year is not leap, move to 28.02 (common workaround)
                next_bday = date(today.year, 2, 28)

            if next_bday < today:
                try:
                    next_bday = next_bday.replace(year=today.year + 1)
                except ValueError:
                    next_bday = date(today.year + 1, 2, 28)

            if today <= next_bday <= end_day:
                cong_date = next_bday
                # 5 = Saturday, 6 = Sunday
                if cong_date.weekday() == 5:
                    cong_date += timedelta(days=2)
                elif cong_date.weekday() == 6:
                    cong_date += timedelta(days=1)

                result.append(
                    {
                        "name": record.name.value,
                        "congratulation_date": cong_date.strftime("%Y.%m.%d"),
                    }
                )

        # Sort by congratulation_date for nicer output
        result.sort(key=lambda x: x["congratulation_date"])
        return result


def parse_input(user_input: str) -> Tuple[str, List[str]]:
    """
    Splits user input into command and args.
    """
    parts = user_input.strip().split()
    if not parts:
        return "", []
    command = parts[0].lower()
    args = parts[1:]
    return command, args


@input_error
def add_contact(args: List[str], book: AddressBook) -> str:
    """
    add [name] [phone]
    Adds new contact or adds phone to existing contact.
    """
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact(args: List[str], book: AddressBook) -> str:
    """
    change [name] [old_phone] [new_phone]
    Changes phone number for contact.
    """
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Phone number changed."


@input_error
def show_phone(args: List[str], book: AddressBook) -> str:
    """
    phone [name]
    Shows all phones for contact.
    """
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return "No phones saved for this contact."
    return ", ".join(p.value for p in record.phones)


@input_error
def show_all(book: AddressBook) -> str:
    """
    all
    Shows all contacts.
    """
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args: List[str], book: AddressBook) -> str:
    """
    add-birthday [name] [DD.MM.YYYY]
    Adds birthday to an existing contact.
    """
    name, bday, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.add_birthday(bday)
    return "Birthday added."


@input_error
def show_birthday(args: List[str], book: AddressBook) -> str:
    """
    show-birthday [name]
    Shows birthday for a contact.
    """
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    return record.show_birthday()


@input_error
def birthdays(book: AddressBook) -> str:
    """
    birthdays
    Shows upcoming birthdays for the next 7 days.
    """
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    lines = [f'{item["name"]}: {item["congratulation_date"]}' for item in upcoming]
    return "\n".join(lines)


def main() -> None:
    """
    Entry point for assistant bot.
    """
    book = AddressBook()
    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break

        if command == "":
            print("Please enter a command.")
            continue

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

    