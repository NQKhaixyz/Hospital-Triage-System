from datetime import datetime
from typing import Dict, List, Tuple, Optional


class Bill:
    """Represents a medical bill for a patient."""

    def __init__(
        self, bill_id: str, patient_id: str, doctor_id: str, department_id: str
    ):
        self.bill_id = bill_id
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.department_id = department_id
        self.items: List[Tuple[str, float]] = []
        self.total_amount = 0.0
        self.is_paid = False
        self.created_at = datetime.now()

    def add_item(self, service_name: str, cost: float) -> None:
        """Add a service item to the bill."""
        self.items.append((service_name, cost))
        self.calculate_total()

    def calculate_total(self) -> float:
        """Calculate the total amount of the bill."""
        self.total_amount = sum(cost for _, cost in self.items)
        return self.total_amount

    def mark_paid(self) -> None:
        """Mark the bill as paid."""
        self.is_paid = True

    def __repr__(self) -> str:
        return f"Bill({self.bill_id}, patient={self.patient_id}, total={self.total_amount}, paid={self.is_paid})"


class BillingSystem:
    """Manages all billing operations for the hospital."""

    # Predefined service catalog
    SERVICE_CATALOG = {
        "consultation": 200000,
        "emergency_care": 500000,
        "blood_test": 150000,
        "xray": 300000,
        "ultrasound": 400000,
        "surgery": 2000000,
        "prescription": 50000,
    }

    def __init__(self):
        self.bills: Dict[str, Bill] = {}
        self.patient_bills: Dict[str, List[str]] = {}
        self.service_catalog: Dict[str, float] = {
            k: float(v) for k, v in self.SERVICE_CATALOG.items()
        }
        self._bill_counter = 0

    def _generate_bill_id(self) -> str:
        """Generate a unique bill ID."""
        self._bill_counter += 1
        return f"BILL{self._bill_counter:06d}"

    def create_bill(
        self,
        patient_id: str,
        doctor_id: str,
        dept_id: str,
        services: Optional[List[str]] = None,
    ) -> Bill:
        """Create a new bill for a patient."""
        if services is None:
            services = []

        bill_id = self._generate_bill_id()
        bill = Bill(bill_id, patient_id, doctor_id, dept_id)

        # Store the bill first so add_service_to_bill can find it
        self.bills[bill_id] = bill

        # Track patient bills
        if patient_id not in self.patient_bills:
            self.patient_bills[patient_id] = []
        self.patient_bills[patient_id].append(bill_id)

        # Add services if provided
        for service_name in services:
            self.add_service_to_bill(bill_id, service_name)

        return bill

    def add_service_to_bill(self, bill_id: str, service_name: str) -> bool:
        """Add a service to an existing bill."""
        if bill_id not in self.bills:
            return False

        if service_name not in self.service_catalog:
            return False

        cost = self.service_catalog[service_name]
        self.bills[bill_id].add_item(service_name, cost)
        return True

    def get_patient_bills(self, patient_id: str) -> List[Bill]:
        """Get all bills for a specific patient."""
        if patient_id not in self.patient_bills:
            return []

        return [self.bills[bill_id] for bill_id in self.patient_bills[patient_id]]

    def get_total_revenue(self) -> float:
        """Get total revenue from all paid bills."""
        return sum(bill.total_amount for bill in self.bills.values() if bill.is_paid)

    def get_department_revenue(self, dept_id: str) -> float:
        """Get total revenue for a specific department."""
        return sum(
            bill.total_amount
            for bill in self.bills.values()
            if bill.department_id == dept_id and bill.is_paid
        )

    def mark_bill_paid(self, bill_id: str) -> bool:
        """Mark a bill as paid."""
        if bill_id not in self.bills:
            return False

        self.bills[bill_id].mark_paid()
        return True

    def add_service_to_catalog(self, service_name: str, base_cost: float) -> None:
        """Add a new service to the catalog."""
        self.service_catalog[service_name] = base_cost


class TriageSystem:
    """Hospital triage system that integrates with billing."""

    def __init__(self):
        self.patients: Dict[str, dict] = {}
        self.doctors: Dict[str, dict] = {}
        self.billing_system = BillingSystem()

    def add_patient(self, patient_id: str, name: str, **kwargs) -> None:
        """Add a patient to the triage system."""
        self.patients[patient_id] = {"name": name, **kwargs}

    def add_doctor(
        self, doctor_id: str, name: str, department_id: str, **kwargs
    ) -> None:
        """Add a doctor to the triage system."""
        self.doctors[doctor_id] = {
            "name": name,
            "department_id": department_id,
            **kwargs,
        }

    def generate_bill_after_examination(
        self, doctor_id: str, patient_id: str, services: List[str]
    ) -> Optional[Bill]:
        """
        Auto-generate a bill when doctor completes examination.

        Args:
            doctor_id: The ID of the examining doctor
            patient_id: The ID of the patient
            services: List of services provided during examination

        Returns:
            The generated Bill or None if doctor/patient not found
        """
        if doctor_id not in self.doctors:
            print(f"Doctor {doctor_id} not found")
            return None

        if patient_id not in self.patients:
            print(f"Patient {patient_id} not found")
            return None

        doctor = self.doctors[doctor_id]
        department_id = doctor.get("department_id", "UNKNOWN")

        # Create bill with services
        bill = self.billing_system.create_bill(
            patient_id=patient_id,
            doctor_id=doctor_id,
            dept_id=department_id,
            services=services,
        )

        print(f"Bill generated: {bill.bill_id} for patient {patient_id}")
        return bill

    def complete_examination(
        self, doctor_id: str, patient_id: str, services: List[str]
    ) -> Optional[Bill]:
        """
        Complete an examination and auto-generate bill.
        This is a convenience method that calls generate_bill_after_examination.
        """
        return self.generate_bill_after_examination(doctor_id, patient_id, services)


# Example usage and testing
if __name__ == "__main__":
    # Initialize the triage system
    triage = TriageSystem()

    # Add doctors
    triage.add_doctor(
        "DOC001", "Dr. Smith", "EMERGENCY", specialty="Emergency Medicine"
    )
    triage.add_doctor("DOC002", "Dr. Johnson", "RADIOLOGY", specialty="Radiology")

    # Add patients
    triage.add_patient("PAT001", "John Doe", age=35, condition="Stable")
    triage.add_patient("PAT002", "Jane Smith", age=28, condition="Critical")

    # Simulate examination and billing
    print("=== Generating Bills After Examinations ===")

    # Patient 1: Emergency care + consultation
    bill1 = triage.complete_examination(
        "DOC001", "PAT001", ["emergency_care", "consultation", "blood_test"]
    )

    # Patient 2: Emergency care + xray + surgery
    bill2 = triage.complete_examination(
        "DOC001", "PAT002", ["emergency_care", "xray", "surgery", "prescription"]
    )

    # Patient 1: Radiology follow-up
    bill3 = triage.complete_examination(
        "DOC002", "PAT001", ["ultrasound", "consultation"]
    )

    print("\n=== Billing Summary ===")
    print(f"Total bills created: {len(triage.billing_system.bills)}")

    # Show patient bills
    print("\n--- Patient PAT001 Bills ---")
    for bill in triage.billing_system.get_patient_bills("PAT001"):
        print(f"  {bill}")
        for service, cost in bill.items:
            print(f"    - {service}: {cost:,.0f}")

    print("\n--- Patient PAT002 Bills ---")
    for bill in triage.billing_system.get_patient_bills("PAT002"):
        print(f"  {bill}")
        for service, cost in bill.items:
            print(f"    - {service}: {cost:,.0f}")

    # Mark bills as paid and show revenue
    print("\n=== Revenue Tracking ===")
    if bill1 and bill2:
        triage.billing_system.mark_bill_paid(bill1.bill_id)
        triage.billing_system.mark_bill_paid(bill2.bill_id)

    print(
        f"Total Revenue (paid bills): {triage.billing_system.get_total_revenue():,.0f}"
    )
    print(
        f"Emergency Department Revenue: {triage.billing_system.get_department_revenue('EMERGENCY'):,.0f}"
    )
    print(
        f"Radiology Department Revenue: {triage.billing_system.get_department_revenue('RADIOLOGY'):,.0f}"
    )

    # Test adding custom service
    print("\n=== Adding Custom Service ===")
    triage.billing_system.add_service_to_catalog("mri_scan", 800000)
    if bill3:
        triage.billing_system.add_service_to_bill(bill3.bill_id, "mri_scan")
        print(f"Updated bill3 total: {bill3.total_amount:,.0f}")

    print("\n=== All Bills ===")
    for bill_id, bill in triage.billing_system.bills.items():
        status = "PAID" if bill.is_paid else "UNPAID"
        print(f"{bill_id}: {bill.patient_id} -> {bill.total_amount:,.0f} ({status})")
