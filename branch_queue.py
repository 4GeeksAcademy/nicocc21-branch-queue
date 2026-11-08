import json
import os
import sys
import tempfile
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SERVICES = ("deposito", "retiro", "gestion_cuenta")
DATA_FILE = Path(__file__).resolve().with_name("branch_queue_data.json")


@dataclass(frozen=True)
class Ticket:
    number: int
    client_name: str
    service_type: str
    issued_at: str


class EmptyQueueError(LookupError):
    """No hay clientes esperando para el servicio solicitado."""


class BranchQueue:
    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.queues = {service: deque() for service in SERVICES}
        self.next_number = 1
        self._load()

    def _load(self):
        try:
            with self.path.open(encoding="utf-8") as file:
                state = json.load(file)
        except FileNotFoundError:
            return

        if not isinstance(state, dict):
            raise ValueError("El estado guardado no es un objeto válido.")
        next_number = state.get("next_number")
        queues = state.get("queues")
        if (type(next_number) is not int or next_number < 1
                or not isinstance(queues, dict) or set(queues) != set(SERVICES)):
            raise ValueError("El contador o las colas guardadas no son válidos.")

        loaded = {}
        numbers = set()
        for service in SERVICES:
            records = queues[service]
            if not isinstance(records, list):
                raise ValueError(f"La cola de {service} no es válida.")
            loaded[service] = deque()
            last_number = 0
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError("Hay un ticket guardado con formato inválido.")
                if set(record) == {"number", "name", "service", "arrived_at"}:
                    record = {
                        "number": record["number"],
                        "client_name": record["name"],
                        "service_type": record["service"],
                        "issued_at": record["arrived_at"],
                    }
                elif set(record) != {
                    "number", "client_name", "service_type", "issued_at"
                }:
                    raise ValueError("Hay un ticket guardado con formato inválido.")
                number = record["number"]
                name = record["client_name"]
                arrived_at = record["issued_at"]
                if (type(number) is not int or not last_number < number < next_number
                        or number in numbers or not isinstance(name, str)
                        or not name.strip() or record["service_type"] != service
                        or not isinstance(arrived_at, str)):
                    raise ValueError("Hay un ticket guardado con datos inválidos.")
                try:
                    datetime.fromisoformat(arrived_at)
                except ValueError as error:
                    raise ValueError("Hay un ticket con una fecha inválida.") from error
                numbers.add(number)
                last_number = number
                loaded[service].append(Ticket(**record))

        self.next_number = next_number
        self.queues = loaded

    def _save(self):
        state = {
            "next_number": self.next_number,
            "queues": {
                service: [asdict(ticket) for ticket in self.queues[service]]
                for service in SERVICES
            },
        }
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as file:
                temporary_path = Path(file.name)
                json.dump(state, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _validate_service(service):
        if service not in SERVICES:
            raise ValueError("Tipo de servicio no válido.")

    def issue_ticket(self, client_name, service_type):
        self._validate_service(service_type)
        if not isinstance(client_name, str) or not client_name.strip():
            raise ValueError("El nombre no puede estar vacío.")
        ticket = Ticket(
            self.next_number, client_name.strip(), service_type,
            datetime.now(timezone.utc).isoformat()
        )
        self.queues[service_type].append(ticket)
        self.next_number += 1
        try:
            self._save()
        except OSError:
            self.queues[service_type].pop()
            self.next_number -= 1
            raise
        return ticket

    def call_next(self, service_type):
        self._validate_service(service_type)
        queue = self.queues[service_type]
        if not queue:
            raise EmptyQueueError(f"No hay clientes esperando para {service_type}.")
        ticket = queue.popleft()
        try:
            self._save()
        except OSError:
            queue.appendleft(ticket)
            raise
        return ticket

    def peek_next(self, service_type):
        self._validate_service(service_type)
        queue = self.queues[service_type]
        return queue[0] if queue else None

    def list_waiting(self):
        return {service: list(self.queues[service]) for service in SERVICES}

    def stats(self):
        counts = {service: len(self.queues[service]) for service in SERVICES}
        counts["total"] = sum(counts.values())
        return counts


def choose_service():
    print("\nServicios:")
    for index, service in enumerate(SERVICES, 1):
        print(f"{index}. {service}")
    choice = input("Seleccione un servicio: ").strip()
    if choice not in ("1", "2", "3"):
        raise ValueError("Seleccione un número de servicio válido.")
    return SERVICES[int(choice) - 1]


def print_ticket(ticket):
    print(
        f"Ticket #{ticket.number} | {ticket.client_name} | {ticket.service_type} "
        f"| Llegada: {ticket.issued_at}"
    )


def main():
    try:
        branch = BranchQueue()
    except (OSError, ValueError, UnicodeError) as error:
        print(f"No se pudo cargar el estado: {error}", file=sys.stderr)
        return 1

    while True:
        print(
            "\n1. Emitir ticket\n2. Llamar al siguiente\n"
            "3. Consultar siguiente\n4. Listar en espera\n"
            "5. Estadísticas\n0. Salir"
        )
        try:
            choice = input("Seleccione una opción: ").strip()
            if choice == "0":
                return 0
            if choice == "1":
                name = input("Nombre del cliente: ")
                ticket = branch.issue_ticket(name, choose_service())
                print("Ticket emitido:")
                print_ticket(ticket)
            elif choice in ("2", "3"):
                service = choose_service()
                ticket = (
                    branch.call_next(service) if choice == "2"
                    else branch.peek_next(service)
                )
                if ticket is None:
                    print("No hay clientes esperando para este servicio.")
                else:
                    print_ticket(ticket)
            elif choice == "4":
                for service, queue in branch.list_waiting().items():
                    print(f"\n{service}:")
                    if not queue:
                        print("  Sin clientes en espera.")
                    for ticket in queue:
                        print_ticket(ticket)
            elif choice == "5":
                for service, count in branch.stats().items():
                    print(f"{service}: {count}")
            else:
                print("Opción no válida.")
        except ValueError as error:
            print(f"Entrada no válida: {error}")
        except EmptyQueueError as error:
            print(error)
        except OSError as error:
            print(f"No se pudo guardar el estado: {error}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
