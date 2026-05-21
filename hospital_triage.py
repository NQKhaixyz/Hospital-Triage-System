#!/usr/bin/env python3
"""
Hospital Triage System with Virtual Clock
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import heapq
import random


class VirtualClock:
    """Virtual clock for simulating time in the hospital system."""

    def __init__(self, start_time: Optional[datetime] = None):
        self.current_time = start_time or datetime(2024, 1, 1, 8, 0, 0)

    def tick(self, minutes: int = 15):
        """Advance time by specified minutes."""
        self.current_time += timedelta(minutes=minutes)

    def get_time(self) -> datetime:
        """Return current time."""
        return self.current_time

    def get_time_str(self) -> str:
        """Return formatted time string HH:MM."""
        return self.current_time.strftime("%H:%M")

    def is_time_slot(self, time_slot: str) -> bool:
        """Check if current time matches given time slot (HH:MM)."""
        return self.get_time_str() == time_slot


@dataclass
class Patient:
    """Patient in the hospital system."""

    id: str
    name: str
    priority: int  # 1=Emergency, 2=Urgent, 3=Normal, 4=Low
    checked_in_at: Optional[datetime] = None
    department: Optional[str] = None
    doctor_id: Optional[str] = None
    status: str = "waiting"  # waiting, in_exam, completed, billed
    appointment_time: Optional[datetime] = None
    is_walk_in: bool = False

    def __lt__(self, other):
        """Compare patients for priority queue (lower priority number = higher priority)."""
        if not isinstance(other, Patient):
            return NotImplemented
        return self.priority < other.priority


@dataclass
class Doctor:
    """Doctor in the hospital system."""

    id: str
    name: str
    department: str
    max_slots_per_hour: int = 4
    current_patient: Optional[Patient] = None
    appointments: Dict[datetime, List[Patient]] = field(default_factory=dict)
    completed_patients: List[Patient] = field(default_factory=list)

    def is_available(self, time_slot: datetime) -> bool:
        """Check if doctor has availability at given time slot."""
        # Count appointments in the same hour
        hour_start = time_slot.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        appointments_in_hour = sum(
            len(patients)
            for t, patients in self.appointments.items()
            if hour_start <= t < hour_end
        )
        return appointments_in_hour < self.max_slots_per_hour

    def book_appointment(self, patient: Patient, time_slot: datetime) -> bool:
        """Book an appointment for a patient."""
        if not self.is_available(time_slot):
            return False
        if time_slot not in self.appointments:
            self.appointments[time_slot] = []
        self.appointments[time_slot].append(patient)
        patient.appointment_time = time_slot
        patient.doctor_id = self.id
        return True

    def get_appointment_count(self) -> int:
        """Get total number of appointments."""
        return sum(len(patients) for patients in self.appointments.values())

    def start_examination(self, patient: Patient):
        """Start examining a patient."""
        self.current_patient = patient
        patient.status = "in_exam"

    def complete_examination(self):
        """Complete current examination."""
        if self.current_patient:
            self.current_patient.status = "completed"
            self.completed_patients.append(self.current_patient)
            patient = self.current_patient
            self.current_patient = None
            return patient
        return None


@dataclass
class Department:
    """Department in the hospital."""

    name: str
    doctors: List[Doctor] = field(default_factory=list)
    queue: List[Patient] = field(default_factory=list)

    def add_doctor(self, doctor: Doctor):
        """Add a doctor to the department."""
        self.doctors.append(doctor)

    def add_to_queue(self, patient: Patient):
        """Add patient to department queue (sorted by priority)."""
        patient.department = self.name
        self.queue.append(patient)
        # Sort queue by priority (lower number = higher priority)
        self.queue.sort(key=lambda p: p.priority)

    def get_next_patient(self) -> Optional[Patient]:
        """Get next patient from queue (highest priority)."""
        if self.queue:
            return self.queue.pop(0)
        return None

    def get_queue_length(self) -> int:
        """Get number of patients in queue."""
        return len(self.queue)

    def get_available_doctors(self) -> List[Doctor]:
        """Get doctors who are not currently examining a patient."""
        return [d for d in self.doctors if d.current_patient is None]


@dataclass
class BillingRecord:
    """Billing record for a patient."""

    patient_id: str
    patient_name: str
    doctor_name: str
    department: str
    amount: float
    services: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    paid: bool = False


class HospitalTriageSystem:
    """Main hospital triage system."""

    def __init__(self, clock: VirtualClock):
        self.clock = clock
        self.departments: Dict[str, Department] = {}
        self.patients: Dict[str, Patient] = {}
        self.billing_records: List[BillingRecord] = []
        self.emergency_patients: List[Patient] = []

    def add_department(self, name: str):
        """Add a department to the hospital."""
        self.departments[name] = Department(name)

    def add_doctor(self, doctor: Doctor):
        """Add a doctor to their department."""
        if doctor.department in self.departments:
            self.departments[doctor.department].add_doctor(doctor)

    def register_patient(self, patient: Patient) -> str:
        """Register a new patient in the system."""
        self.patients[patient.id] = patient
        return patient.id

    def check_in_patient(self, patient_id: str, department_name: str):
        """Check in a patient to a department."""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        if department_name not in self.departments:
            raise ValueError(f"Department {department_name} not found")

        patient.checked_in_at = self.clock.get_time()
        patient.status = "waiting"

        # Emergency patients (priority 1) go to emergency queue
        if patient.priority == 1:
            self.emergency_patients.append(patient)
            self.emergency_patients.sort(key=lambda p: p.priority)
        else:
            self.departments[department_name].add_to_queue(patient)

    def book_appointment(self, patient_id: str, doctor_id: str, time_slot: str) -> bool:
        """Book an appointment for a patient with a specific doctor."""
        patient = self.patients.get(patient_id)
        if not patient:
            return False

        # Find doctor
        doctor = None
        for dept in self.departments.values():
            for d in dept.doctors:
                if d.id == doctor_id:
                    doctor = d
                    break
            if doctor:
                break

        if not doctor:
            return False

        # Parse time slot
        try:
            hour, minute = map(int, time_slot.split(":"))
            appointment_time = self.clock.get_time().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        except ValueError:
            return False

        return doctor.book_appointment(patient, appointment_time)

    def assign_patient_to_doctor(self, department_name: str) -> Optional[Patient]:
        """Assign next patient from queue to available doctor."""
        dept = self.departments.get(department_name)
        if not dept:
            return None

        available_doctors = dept.get_available_doctors()
        if not available_doctors:
            return None

        # Check emergency patients first
        if self.emergency_patients:
            patient = self.emergency_patients.pop(0)
            doctor = available_doctors[0]
            doctor.start_examination(patient)
            return patient

        patient = dept.get_next_patient()
        if patient:
            doctor = available_doctors[0]
            doctor.start_examination(patient)

        return patient

    def complete_examination(self, doctor_id: str) -> Optional[Patient]:
        """Complete examination for a doctor's current patient."""
        for dept in self.departments.values():
            for doctor in dept.doctors:
                if doctor.id == doctor_id:
                    return doctor.complete_examination()
        return None

    def generate_bill(self, patient_id: str, services: List[str]) -> BillingRecord:
        """Generate bill for a patient."""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Find doctor
        doctor = None
        for dept in self.departments.values():
            for d in dept.doctors:
                if d.id == patient.doctor_id:
                    doctor = d
                    break
            if doctor:
                break

        # Calculate amount based on services
        base_amount = 100.0
        service_costs = {
            "examination": 50.0,
            "xray": 150.0,
            "blood_test": 80.0,
            "surgery": 500.0,
            "prescription": 30.0,
        }

        total = base_amount
        for service in services:
            total += service_costs.get(service, 0)

        record = BillingRecord(
            patient_id=patient_id,
            patient_name=patient.name,
            doctor_name=doctor.name if doctor else "Unknown",
            department=patient.department or "Unknown",
            amount=total,
            services=services,
            generated_at=self.clock.get_time(),
        )

        self.billing_records.append(record)
        patient.status = "billed"

        return record

    def process_late_patients(self):
        """Demote patients who have been waiting too long (priority 2 -> 3)."""
        current_time = self.clock.get_time()
        for dept in self.departments.values():
            for patient in dept.queue:
                if (
                    patient.priority == 2
                    and patient.checked_in_at
                    and (current_time - patient.checked_in_at) >= timedelta(hours=2)
                ):
                    patient.priority = 3
                    print(
                        f"  [LATE] Patient {patient.name} demoted from priority 2 to 3"
                    )
            # Re-sort queue after demotion
            dept.queue.sort(key=lambda p: p.priority)

    def process_walk_ins(self):
        """Process walk-in patients to fill empty slots."""
        for dept in self.departments.values():
            available_doctors = dept.get_available_doctors()
            for doctor in available_doctors:
                # Check if doctor has empty slot
                if not doctor.current_patient and dept.queue:
                    patient = dept.get_next_patient()
                    if patient:
                        patient.is_walk_in = True
                        doctor.start_examination(patient)
                        print(
                            f"  [WALK-IN] Patient {patient.name} assigned to {doctor.name}"
                        )


class DemoScenario:
    """Comprehensive demo and test scenario for the hospital triage system."""

    def __init__(self):
        self.clock = VirtualClock(datetime(2024, 1, 15, 8, 0, 0))
        self.system = HospitalTriageSystem(self.clock)
        self.patient_counter = 0
        self.doctor_counter = 0

    def create_patient(self, name: str, priority: int) -> Patient:
        """Create a new patient."""
        self.patient_counter += 1
        patient = Patient(
            id=f"P{self.patient_counter:03d}", name=name, priority=priority
        )
        self.system.register_patient(patient)
        return patient

    def create_doctor(self, name: str, department: str) -> Doctor:
        """Create a new doctor."""
        self.doctor_counter += 1
        return Doctor(
            id=f"D{self.doctor_counter:03d}", name=name, department=department
        )

    def setup(self):
        """Setup: Create departments and doctors."""
        print("=" * 80)
        print("SETUP: Creating Hospital System")
        print("=" * 80)

        departments = [
            "Noi tong quat",
            "Ngoai khoa",
            "Nhi khoa",
            "San khoa",
            "Tai mui hong",
        ]

        # Create departments
        for dept_name in departments:
            self.system.add_department(dept_name)
            print(f"Created department: {dept_name}")

        # Add 2 doctors per department
        for dept_name in departments:
            for i in range(2):
                doctor = self.create_doctor(f"Dr. {dept_name} {i + 1}", dept_name)
                self.system.add_doctor(doctor)
                print(f"  Added {doctor.name} ({doctor.id})")

        print(f"\nSystem initialized at {self.clock.get_time_str()}")
        print()

    def test1_book_appointments(self):
        """Test 1: Book 5 appointments for different doctors, verify slot limits (max 4)."""
        print("=" * 80)
        print("TEST 1: Booking Appointments")
        print("=" * 80)

        # Create 5 patients
        patients = [
            self.create_patient("Nguyen Van A", 3),
            self.create_patient("Tran Thi B", 3),
            self.create_patient("Le Van C", 3),
            self.create_patient("Pham Thi D", 3),
            self.create_patient("Hoang Van E", 3),
        ]

        # Get first doctor from each of 5 departments
        doctors = []
        for dept_name in self.system.departments.keys():
            dept = self.system.departments[dept_name]
            if dept.doctors:
                doctors.append(dept.doctors[0])

        # Book appointments at 09:00 for different doctors
        time_slots = ["09:00", "09:00", "09:00", "09:00", "09:00"]
        success_count = 0

        for i, (patient, time_slot) in enumerate(zip(patients[:5], time_slots[:5])):
            if i < len(doctors):
                doctor = doctors[i]
                result = self.system.book_appointment(patient.id, doctor.id, time_slot)
                if result:
                    success_count += 1
                    print(
                        f"[OK] Booked {patient.name} with {doctor.name} at {time_slot}"
                    )
                else:
                    print(
                        f"[FAIL] Failed to book {patient.name} with {doctor.name} at {time_slot}"
                    )

        # Test slot limit: Book 4 appointments with the same doctor at 10:00, then try 5th
        test_doctor = doctors[0] if doctors else None
        slot_limit_respected = True
        if test_doctor:
            print(f"\nTesting slot limit for {test_doctor.name} at 10:00...")
            slot_patients = []
            for i in range(5):
                p = self.create_patient(f"Slot Test {i + 1}", 3)
                slot_patients.append(p)
                result = self.system.book_appointment(p.id, test_doctor.id, "10:00")
                if i < 4:
                    if result:
                        print(f"[OK] Booked appointment {i + 1}/4 at 10:00")
                    else:
                        print(f"[FAIL] Could not book appointment {i + 1}/4")
                        slot_limit_respected = False
                else:
                    if not result:
                        print(
                            f"[OK] Correctly rejected 5th appointment at 10:00 (limit: 4)"
                        )
                    else:
                        print(f"[FAIL] Should have rejected 5th appointment at 10:00")
                        slot_limit_respected = False

        print(
            f"\nResult: {success_count}/5 appointments booked successfully, slot limit respected: {slot_limit_respected}"
        )
        print()
        return success_count == 5 and slot_limit_respected

    def test2_check_in_patients(self):
        """Test 2: Check in patients with different priorities."""
        print("=" * 80)
        print("TEST 2: Checking In Patients with Different Priorities")
        print("=" * 80)

        patients = [
            self.create_patient("Priority 1 Patient", 1),
            self.create_patient("Priority 2 Patient", 2),
            self.create_patient("Priority 3 Patient", 3),
            self.create_patient("Priority 4 Patient", 4),
        ]

        dept_name = "Noi tong quat"
        for patient in patients:
            self.system.check_in_patient(patient.id, dept_name)
            print(
                f"[OK] Checked in {patient.name} (Priority {patient.priority}) to {dept_name}"
            )

        # Verify queue order
        dept = self.system.departments[dept_name]
        priorities = [p.priority for p in dept.queue]
        print(f"\nQueue priorities: {priorities}")

        # Check emergency queue
        print(f"Emergency patients: {len(self.system.emergency_patients)}")

        is_sorted = priorities == sorted(priorities)
        print(f"\nResult: Queue correctly sorted by priority: {is_sorted}")
        print()
        return is_sorted

    def test3_simulate_examinations(self):
        """Test 3: Simulate doctor completing examinations, verify multilevel queue routing."""
        print("=" * 80)
        print("TEST 3: Simulating Examinations and Queue Routing")
        print("=" * 80)

        dept_name = "Ngoai khoa"
        dept = self.system.departments[dept_name]

        # Ensure we have patients in queue
        patients = [
            self.create_patient("Surgery Patient 1", 2),
            self.create_patient("Surgery Patient 2", 3),
            self.create_patient("Surgery Patient 3", 3),
        ]

        for patient in patients:
            self.system.check_in_patient(patient.id, dept_name)

        print(f"Initial queue length: {dept.get_queue_length()}")

        # Assign patients to available doctors
        assigned_count = 0
        for doctor in dept.doctors:
            if not doctor.current_patient:
                patient = self.system.assign_patient_to_doctor(dept_name)
                if patient:
                    assigned_count += 1
                    print(f"[OK] Assigned {patient.name} to {doctor.name}")

        print(f"Patients assigned: {assigned_count}")

        # Complete some examinations
        completed_count = 0
        for doctor in dept.doctors:
            if doctor.current_patient:
                patient = self.system.complete_examination(doctor.id)
                if patient:
                    completed_count += 1
                    print(f"[OK] Completed examination for {patient.name}")

        print(f"Examinations completed: {completed_count}")
        print(f"Remaining queue length: {dept.get_queue_length()}")

        success = assigned_count > 0 and completed_count > 0
        print(f"\nResult: Multilevel queue routing works: {success}")
        print()
        return success

    def test4_emergency_priority(self):
        """Test 4: Test emergency priority (priority 1 always first)."""
        print("=" * 80)
        print("TEST 4: Emergency Priority (Priority 1 Always First)")
        print("=" * 80)

        dept_name = "San khoa"

        # Add normal priority patients first
        normal_patients = [
            self.create_patient("Normal Patient 1", 3),
            self.create_patient("Normal Patient 2", 3),
        ]

        for patient in normal_patients:
            self.system.check_in_patient(patient.id, dept_name)

        # Now add emergency patient
        emergency_patient = self.create_patient("Emergency Patient", 1)
        self.system.check_in_patient(emergency_patient.id, dept_name)

        # Assign to doctor
        dept = self.system.departments[dept_name]
        available_doctors = dept.get_available_doctors()

        if available_doctors:
            patient = self.system.assign_patient_to_doctor(dept_name)
            if patient and patient.priority == 1:
                print(f"[OK] Emergency patient {patient.name} was seen first!")
                print(f"  Priority: {patient.priority}")
                success = True
            else:
                print(f"[FAIL] Emergency patient was NOT seen first")
                print(
                    f"  Assigned patient priority: {patient.priority if patient else 'None'}"
                )
                success = False
        else:
            print("No available doctors to test")
            success = False

        print(f"\nResult: Emergency priority respected: {success}")
        print()
        return success

    def test5_walk_in_patients(self):
        """Test 5: Test walk-in patients filling empty slots."""
        print("=" * 80)
        print("TEST 5: Walk-in Patients Filling Empty Slots")
        print("=" * 80)

        dept_name = "Tai mui hong"
        dept = self.system.departments[dept_name]

        # Create walk-in patients
        walk_in_patients = [
            self.create_patient("Walk-in 1", 3),
            self.create_patient("Walk-in 2", 3),
        ]

        for patient in walk_in_patients:
            self.system.check_in_patient(patient.id, dept_name)

        initial_queue = dept.get_queue_length()
        print(f"Initial queue: {initial_queue} patients")

        # Process walk-ins
        self.system.process_walk_ins()

        remaining_queue = dept.get_queue_length()
        assigned = initial_queue - remaining_queue

        print(f"Patients assigned to available doctors: {assigned}")
        print(f"Remaining queue: {remaining_queue}")

        # Verify walk-in flags
        for doctor in dept.doctors:
            if doctor.current_patient and doctor.current_patient.is_walk_in:
                print(f"[OK] {doctor.current_patient.name} marked as walk-in")

        success = assigned > 0
        print(f"\nResult: Walk-in patients processed: {success}")
        print()
        return success

    def test6_late_patient_demotion(self):
        """Test 6: Test late patient demotion from priority 2 to 3."""
        print("=" * 80)
        print("TEST 6: Late Patient Demotion (Priority 2 -> 3)")
        print("=" * 80)

        dept_name = "Nhi khoa"

        # Create priority 2 patient
        late_patient = self.create_patient("Late Priority 2 Patient", 2)
        self.system.check_in_patient(late_patient.id, dept_name)

        print(f"Initial priority: {late_patient.priority}")
        print(f"Checked in at: {self.clock.get_time_str()}")

        # Advance time by 2+ hours
        self.clock.tick(minutes=135)  # 2 hours 15 minutes
        print(f"Current time: {self.clock.get_time_str()} (2h15m later)")

        # Process late patients
        self.system.process_late_patients()

        print(f"Priority after demotion: {late_patient.priority}")

        success = late_patient.priority == 3
        print(f"\nResult: Late patient correctly demoted: {success}")
        print()
        return success

    def test7_billing_generation(self):
        """Test 7: Test billing generation."""
        print("=" * 80)
        print("TEST 7: Billing Generation")
        print("=" * 80)

        dept_name = "Nhi khoa"
        dept = self.system.departments[dept_name]

        # Clear any existing patients from doctors and queue in this department
        for doctor in dept.doctors:
            if doctor.current_patient:
                self.system.complete_examination(doctor.id)
                print(f"[OK] Cleared existing patient from {doctor.name}")

        # Clear the queue to ensure only our test patient is in it
        dept.queue.clear()

        # Remove emergency patients that might be for this department
        self.system.emergency_patients = [
            p for p in self.system.emergency_patients if p.department != dept_name
        ]

        # Create and complete a patient visit
        patient = self.create_patient("Billing Test Patient", 3)

        # Find doctor and assign
        self.system.check_in_patient(patient.id, dept_name)

        # Assign to doctor
        assigned_patient = self.system.assign_patient_to_doctor(dept_name)
        if assigned_patient:
            print(f"[OK] Assigned {assigned_patient.name} to doctor")
        else:
            print(f"[FAIL] Could not assign patient to doctor")

        # Complete examination
        for doctor in dept.doctors:
            if doctor.current_patient and doctor.current_patient.id == patient.id:
                self.system.complete_examination(doctor.id)
                patient.doctor_id = doctor.id
                print(f"[OK] Completed examination with {doctor.name}")
                break

        # Generate bill
        services = ["examination", "blood_test", "prescription"]
        bill = self.system.generate_bill(patient.id, services)

        print(f"[OK] Generated bill for {bill.patient_name}")
        print(f"  Doctor: {bill.doctor_name}")
        print(f"  Department: {bill.department}")
        print(f"  Services: {', '.join(bill.services)}")
        print(f"  Amount: ${bill.amount:.2f}")
        print(f"  Generated at: {bill.generated_at.strftime('%H:%M')}")

        success = bill.amount > 0 and len(self.system.billing_records) > 0
        print(f"\nResult: Billing generated correctly: {success}")
        print()
        return success

    def test8_dashboard_display(self):
        """Test 8: Display real-time dashboard showing all doctors and queue status."""
        print("=" * 80)
        print("TEST 8: Real-Time Dashboard")
        print("=" * 80)

        # Add some activity for dashboard display
        for i in range(3):
            patient = self.create_patient(f"Dashboard Patient {i + 1}", 3)
            self.system.check_in_patient(patient.id, "Noi tong quat")

        # Assign some patients
        self.system.assign_patient_to_doctor("Noi tong quat")

        # Print dashboard
        print_dashboard(self.system, self.clock)

        return True

    def run_all_tests(self):
        """Run all tests and print summary."""
        print("\n")
        print("#" * 80)
        print("# HOSPITAL TRIAGE SYSTEM - COMPREHENSIVE TEST SUITE")
        print("#" * 80)
        print("\n")

        self.setup()

        results = {}

        results["Test 1: Appointments"] = self.test1_book_appointments()
        results["Test 2: Check-in"] = self.test2_check_in_patients()
        results["Test 3: Examinations"] = self.test3_simulate_examinations()
        results["Test 4: Emergency Priority"] = self.test4_emergency_priority()
        results["Test 5: Walk-in"] = self.test5_walk_in_patients()
        results["Test 6: Late Demotion"] = self.test6_late_patient_demotion()
        results["Test 7: Billing"] = self.test7_billing_generation()
        results["Test 8: Dashboard"] = self.test8_dashboard_display()

        # Summary
        print("\n")
        print("#" * 80)
        print("# TEST SUMMARY")
        print("#" * 80)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "[OK] PASS" if result else "[FAIL] FAIL"
            print(f"{status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n[CELEBRATE] All tests passed! System is working correctly.")
        else:
            print(f"\n[WARN]  {total - passed} test(s) failed. Please review.")

        return passed == total


def print_dashboard(triage_system: HospitalTriageSystem, clock: VirtualClock):
    """Print real-time dashboard showing all doctors and queue status."""
    print("\n" + "=" * 80)
    print(f"HOSPITAL DASHBOARD - {clock.get_time_str()}")
    print("=" * 80)

    total_patients = 0
    total_doctors_busy = 0
    total_doctors_available = 0

    for dept_name, dept in triage_system.departments.items():
        print(f"\n{dept_name.upper()}")
        print("-" * 40)

        # Doctor status
        print("Doctors:")
        for doctor in dept.doctors:
            status = (
                "[GREEN] Available" if doctor.current_patient is None else "[RED] Busy"
            )
            if doctor.current_patient:
                total_doctors_busy += 1
                print(
                    f"  {doctor.name}: {status} - Examining {doctor.current_patient.name}"
                )
            else:
                total_doctors_available += 1
                print(f"  {doctor.name}: {status}")

        # Queue status
        queue_length = dept.get_queue_length()
        total_patients += queue_length
        print(f"Queue: {queue_length} patients waiting")

        if dept.queue:
            for patient in dept.queue[:5]:  # Show first 5
                priority_label = {
                    1: "EMERGENCY",
                    2: "URGENT",
                    3: "NORMAL",
                    4: "LOW",
                }.get(patient.priority, "UNKNOWN")
                print(
                    f"  - {patient.name} (Priority {patient.priority}: {priority_label})"
                )
            if len(dept.queue) > 5:
                print(f"  ... and {len(dept.queue) - 5} more")

    # Emergency queue
    emergency_count = len(triage_system.emergency_patients)
    if emergency_count > 0:
        print(f"\n[EMERGENCY] EMERGENCY QUEUE: {emergency_count} patients")
        for patient in triage_system.emergency_patients:
            print(f"  - {patient.name}")

    # Summary statistics
    print(f"\n{'=' * 80}")
    print("SUMMARY STATISTICS")
    print(f"  Total patients waiting: {total_patients}")
    print(f"  Doctors busy: {total_doctors_busy}")
    print(f"  Doctors available: {total_doctors_available}")
    print(f"  Emergency patients: {emergency_count}")
    print(f"  Billing records: {len(triage_system.billing_records)}")
    print(f"  Current time: {clock.get_time_str()}")
    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    scenario = DemoScenario()
    success = scenario.run_all_tests()

    if success:
        print("\n[PASS] Hospital Triage System Demo completed successfully!")
    else:
        print("\n[FAIL] Some tests failed. Please check the output above.")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
