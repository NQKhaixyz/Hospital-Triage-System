from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, Any


class Patient:
    def __init__(
        self, patient_id, name, age=0, symptoms="", danger_level=2, is_booked=False
    ):
        self.patient_id = patient_id
        self.name = name
        self.age = age
        self.symptoms = symptoms
        self.danger_level = danger_level
        self.is_booked = is_booked
        self.ticket_number = ""
        self.appointment_time: Optional[datetime] = None
        self.doctor_id: Optional[str] = None
        self.arrival_time = datetime.now()
        self.wait_start_time = datetime.now()
        self.doctor_ids: Set[str] = set()
        self.priority = danger_level

    def __repr__(self):
        return f"<Patient(id={self.patient_id}, name='{self.name}', ticket={self.ticket_number})>"


class Doctor:
    def __init__(self, doctor_id, name, department_id):
        self.doctor_id = doctor_id
        self.name = name
        self.department_id = department_id
        self.booked_queue = deque()
        self.current_patient_id = None
        self.is_idle = True

    def __repr__(self):
        return f"<Doctor(id={self.doctor_id}, name='{self.name}')>"


class Department:
    def __init__(self, department_id, name):
        self.department_id = department_id
        self.name = name
        self.emergency_queue = deque()
        self.walk_in_queue = deque()
        self.priority_queue = deque()
        self.doctor_ids: Set[str] = set()

    def __repr__(self):
        return f"<Department(id={self.department_id}, name='{self.name}')>"


class TriageSystem:
    def __init__(self):
        self.patients = {}
        self.doctors = {}
        self.departments = {}
        self.appointment_slots = {}
        self.scheduled_appointments = {}
        self.walk_in_counter = 0
        self.booked_counter = 0

        # Many-to-many relationship graphs
        self.doctor_patient_graph: Dict[str, Set[str]] = {}
        self.patient_doctor_graph: Dict[str, Set[str]] = {}

    def _get_next_booked_ticket(self):
        self.booked_counter += 1
        return f"B-{self.booked_counter:03d}"

    def book_appointment(self, patient_data, date, time_slot, doctor_id):
        slot_key = (date, time_slot, doctor_id)

        current_bookings = self.appointment_slots.get(slot_key, 0)
        if current_bookings >= 4:
            return {"status": "failure", "message": "Slot is full (max 4 patients)"}

        patient_id = patient_data.get("patient_id")
        if patient_id not in self.patients:
            patient = Patient(
                patient_id=patient_id,
                name=patient_data.get("name", "Unknown"),
                age=patient_data.get("age", 0),
                symptoms=patient_data.get("symptoms", ""),
                danger_level=2,
                is_booked=True,
            )
            self.patients[patient_id] = patient
        else:
            patient = self.patients[patient_id]
            patient.is_booked = True

        ticket = self._get_next_booked_ticket()
        patient.ticket_number = ticket

        if slot_key not in self.scheduled_appointments:
            self.scheduled_appointments[slot_key] = []

        appointment = {
            "patient_id": patient_id,
            "ticket_number": ticket,
            "date": date,
            "time_slot": time_slot,
            "doctor_id": doctor_id,
            "patient_name": patient.name,
        }
        self.scheduled_appointments[slot_key].append(appointment)

        self.appointment_slots[slot_key] = current_bookings + 1

        return {
            "status": "success",
            "message": f"Appointment booked. Ticket: {ticket}",
            "ticket_number": ticket,
            "appointment": appointment,
        }

    def cancel_appointment(self, patient_id, date, time_slot, doctor_id):
        slot_key = (date, time_slot, doctor_id)

        if slot_key not in self.scheduled_appointments:
            return {"status": "failure", "message": "Appointment not found"}

        appointments = self.scheduled_appointments[slot_key]
        appointment_to_remove = None
        for app in appointments:
            if app["patient_id"] == patient_id:
                appointment_to_remove = app
                break

        if appointment_to_remove is None:
            return {
                "status": "failure",
                "message": "Appointment not found for this patient",
            }

        appointments.remove(appointment_to_remove)

        if not appointments:
            del self.scheduled_appointments[slot_key]

        self.appointment_slots[slot_key] = self.appointment_slots.get(slot_key, 0) - 1
        if self.appointment_slots[slot_key] <= 0:
            del self.appointment_slots[slot_key]

        if patient_id in self.patients:
            self.patients[patient_id].is_booked = False

        return {
            "status": "success",
            "message": "Appointment cancelled successfully",
            "cancelled_appointment": appointment_to_remove,
        }

    def get_available_slots(self, date, doctor_id):
        available = []
        for slot_key, count in self.appointment_slots.items():
            d, time_slot, doc_id = slot_key
            if d == date and doc_id == doctor_id and count < 4:
                available.append(time_slot)

        return {
            "status": "success",
            "date": date,
            "doctor_id": doctor_id,
            "available_slots": available,
            "count": len(available),
        }

    def get_doctor_appointments(self, doctor_id, date):
        results = []
        for slot_key, appointments in self.scheduled_appointments.items():
            d, time_slot, doc_id = slot_key
            if d == date and doc_id == doctor_id:
                results.extend(appointments)

        return {
            "status": "success",
            "doctor_id": doctor_id,
            "date": date,
            "appointments": results,
            "count": len(results),
        }

    def next_patient_for_doctor(self, doctor_id, current_time=None):
        """Get next patient using multilevel queue routing."""
        if doctor_id not in self.doctors:
            return None

        doctor = self.doctors[doctor_id]
        department = self.departments.get(doctor.department_id)
        if not department:
            return None

        current_time = current_time or datetime.now()
        patient_to_assign = None

        def get_patient_from_queue_item(item):
            """Helper to get Patient object from queue item (either string ID or Patient object)."""
            if isinstance(item, str):
                return self.patients.get(item)
            return item

        # Priority 1: Check emergency queue
        if department.emergency_queue:
            patient_to_assign = get_patient_from_queue_item(
                department.emergency_queue.popleft()
            )

        # Priority 2: Check booked appointments with time validation (15 min window)
        elif doctor.booked_queue:
            next_booked = get_patient_from_queue_item(doctor.booked_queue[0])
            if next_booked and next_booked.appointment_time:
                time_diff = abs(
                    (current_time - next_booked.appointment_time).total_seconds() / 60
                )
                if time_diff <= 15:
                    patient_to_assign = get_patient_from_queue_item(
                        doctor.booked_queue.popleft()
                    )

        # Priority 3: Check walk-in queue
        if patient_to_assign is None and department.walk_in_queue:
            patient_to_assign = get_patient_from_queue_item(
                department.walk_in_queue.popleft()
            )

        # Fallback: Check booked queue again with relaxed timing (up to 15 min before)
        if patient_to_assign is None and doctor.booked_queue:
            next_booked = get_patient_from_queue_item(doctor.booked_queue[0])
            if next_booked and next_booked.appointment_time:
                time_diff = (
                    current_time - next_booked.appointment_time
                ).total_seconds() / 60
                if time_diff > -15:
                    patient_to_assign = get_patient_from_queue_item(
                        doctor.booked_queue.popleft()
                    )

        if patient_to_assign:
            # Save to many-to-many relationship graphs
            if doctor_id not in self.doctor_patient_graph:
                self.doctor_patient_graph[doctor_id] = set()
            self.doctor_patient_graph[doctor_id].add(patient_to_assign.patient_id)

            if patient_to_assign.patient_id not in self.patient_doctor_graph:
                self.patient_doctor_graph[patient_to_assign.patient_id] = set()
            self.patient_doctor_graph[patient_to_assign.patient_id].add(doctor_id)

            patient_to_assign.doctor_ids.add(doctor_id)
            patient_to_assign.wait_start_time = current_time
            doctor.current_patient_id = patient_to_assign.patient_id
            doctor.is_idle = False
            return patient_to_assign
        else:
            doctor.current_patient_id = None
            doctor.is_idle = True
            return None

        doctor = self.doctors[doctor_id]
        department = self.departments.get(doctor.department_id)
        if not department:
            return None

        current_time = current_time or datetime.now()
        patient_to_assign = None

        # Priority 1: Emergency queue
        if department.emergency_queue:
            patient_to_assign = department.emergency_queue.popleft()
        # Priority 2: Booked appointments (15 min window)
        elif doctor.booked_queue:
            next_booked = doctor.booked_queue[0]
            if next_booked.appointment_time:
                time_diff = abs(
                    (current_time - next_booked.appointment_time).total_seconds() / 60
                )
                if time_diff <= 15:
                    patient_to_assign = doctor.booked_queue.popleft()
        # Priority 3: Walk-in queue
        if patient_to_assign is None and department.walk_in_queue:
            patient_to_assign = department.walk_in_queue.popleft()
        # Fallback: booked appointment within 15 min before
        if patient_to_assign is None and doctor.booked_queue:
            next_booked = doctor.booked_queue[0]
            if next_booked.appointment_time:
                time_diff = (
                    current_time - next_booked.appointment_time
                ).total_seconds() / 60
                if time_diff > -15:
                    patient_to_assign = doctor.booked_queue.popleft()

        if patient_to_assign:
            # Save to many-to-many relationship graphs
            if doctor_id not in self.doctor_patient_graph:
                self.doctor_patient_graph[doctor_id] = set()
            self.doctor_patient_graph[doctor_id].add(patient_to_assign.patient_id)

            if patient_to_assign.patient_id not in self.patient_doctor_graph:
                self.patient_doctor_graph[patient_to_assign.patient_id] = set()
            self.patient_doctor_graph[patient_to_assign.patient_id].add(doctor_id)

            patient_to_assign.doctor_ids.add(doctor_id)
            patient_to_assign.wait_start_time = current_time
            doctor.current_patient_id = patient_to_assign.patient_id
            doctor.is_idle = False
            return patient_to_assign
        else:
            doctor.current_patient_id = None
            doctor.is_idle = True
            return None

    def complete_examination(self, doctor_id):
        """Complete exam and get next patient. Print status message."""
        if doctor_id not in self.doctors:
            return None
        doctor = self.doctors[doctor_id]
        next_patient = self.next_patient_for_doctor(doctor_id)
        if next_patient:
            print(
                f"Doctor {doctor.name} is now examining Patient {next_patient.name} "
                f"(Priority: {next_patient.priority}, Ticket: {next_patient.ticket_number})"
            )
        else:
            print(f"Doctor {doctor.name} is now idle - no patients available")
        return next_patient

    def get_doctor_status(self, doctor_id):
        """Return current patient info and queue lengths for this doctor."""
        if doctor_id not in self.doctors:
            return {"error": f"Doctor {doctor_id} not found"}
        doctor = self.doctors[doctor_id]
        department = self.departments.get(doctor.department_id)
        current_patient = None
        if doctor.current_patient_id and doctor.current_patient_id in self.patients:
            current_patient = self.patients[doctor.current_patient_id]
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor.name,
            "department": department.name if department else "Unknown",
            "is_idle": doctor.is_idle,
            "current_patient": {
                "patient_id": current_patient.patient_id,
                "name": current_patient.name,
                "priority": current_patient.priority,
                "ticket_number": current_patient.ticket_number,
            }
            if current_patient
            else None,
            "queue_lengths": {
                "booked_queue": len(doctor.booked_queue),
                "emergency_queue": len(department.emergency_queue) if department else 0,
                "walk_in_queue": len(department.walk_in_queue) if department else 0,
                "priority_queue": len(department.priority_queue) if department else 0,
            },
            "total_patients_seen": len(self.doctor_patient_graph.get(doctor_id, set())),
        }

    def get_all_departments_status(self):
        """Return comprehensive status of all departments, doctors, queue lengths."""
        status = {
            "departments": {},
            "summary": {
                "total_departments": len(self.departments),
                "total_doctors": len(self.doctors),
                "total_patients": len(self.patients),
                "total_idle_doctors": 0,
                "total_active_doctors": 0,
            },
        }
        for dept_id, department in self.departments.items():
            dept_status = {
                "dept_id": dept_id,
                "name": department.name,
                "queue_lengths": {
                    "emergency_queue": len(department.emergency_queue),
                    "walk_in_queue": len(department.walk_in_queue),
                    "priority_queue": len(department.priority_queue),
                },
                "doctors": [],
            }
            for doctor_id in department.doctor_ids:
                doctor = self.doctors[doctor_id]
                doctor_status = self.get_doctor_status(doctor_id)
                dept_status["doctors"].append(doctor_status)
                if doctor.is_idle:
                    status["summary"]["total_idle_doctors"] += 1
                else:
                    status["summary"]["total_active_doctors"] += 1
            status["departments"][dept_id] = dept_status
        return status

    def promote_waited_patients(self, dept_id, max_wait_minutes=120):
        """Check walk_in_queue for patients waiting too long. Implement aging mechanism."""
        if dept_id not in self.departments:
            return []
        department = self.departments[dept_id]
        current_time = datetime.now()
        promoted_patients = []

        def get_patient(item):
            if isinstance(item, str):
                return self.patients.get(item)
            return item

        # Check walk_in_queue for long waits
        patients_to_keep = deque()
        while department.walk_in_queue:
            patient = get_patient(department.walk_in_queue.popleft())
            if patient is None:
                continue
            wait_time = (current_time - patient.wait_start_time).total_seconds() / 60
            if wait_time >= max_wait_minutes and patient.priority > 1:
                old_priority = patient.priority
                patient.priority = 2
                department.priority_queue.append(patient)
                promoted_patients.append(patient)
                print(
                    f"Patient {patient.name} (Ticket: {patient.ticket_number}) promoted "
                    f"from priority {old_priority} to 2 after waiting {wait_time:.1f} minutes"
                )
            else:
                patients_to_keep.append(patient)
        department.walk_in_queue = patients_to_keep

        # Check priority_queue for extended waits (1.5x max)
        priority_to_keep = deque()
        while department.priority_queue:
            patient = get_patient(department.priority_queue.popleft())
            if patient is None:
                continue
            wait_time = (current_time - patient.wait_start_time).total_seconds() / 60
            if wait_time >= max_wait_minutes * 1.5 and patient.priority > 1:
                patient.priority = 1
                department.emergency_queue.append(patient)
                promoted_patients.append(patient)
                print(
                    f"Patient {patient.name} further promoted to emergency priority after "
                    f"extended wait of {wait_time:.1f} minutes"
                )
            else:
                priority_to_keep.append(patient)
        department.priority_queue = priority_to_keep

        return promoted_patients

    def add_to_emergency_queue(self, dept_id, patient):
        """Add patient to emergency queue with priority 1."""
        if dept_id not in self.departments:
            return False
        patient.priority = 1
        patient.wait_start_time = datetime.now()
        self.departments[dept_id].emergency_queue.append(patient)
        if patient.patient_id not in self.patients:
            self.patients[patient.patient_id] = patient
        return True

    def add_to_walk_in_queue(self, dept_id, patient):
        """Add patient to walk-in queue."""
        if dept_id not in self.departments:
            return False
        patient.wait_start_time = datetime.now()
        self.departments[dept_id].walk_in_queue.append(patient)
        if patient.patient_id not in self.patients:
            self.patients[patient.patient_id] = patient
        return True

    def add_to_booked_queue(self, doctor_id, patient, appointment_time):
        """Add patient to doctor's booked queue."""
        if doctor_id not in self.doctors:
            return False
        patient.appointment_time = appointment_time
        patient.priority = 2
        self.doctors[doctor_id].booked_queue.append(patient)
        if patient.patient_id not in self.patients:
            self.patients[patient.patient_id] = patient
        return True

    def print_system_status(self):
        """Print formatted system status."""
        status = self.get_all_departments_status()
        print("\n" + "=" * 60)
        print("HOSPITAL TRIAGE SYSTEM STATUS")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  Total Departments: {status['summary']['total_departments']}")
        print(f"  Total Doctors: {status['summary']['total_doctors']}")
        print(f"  Total Patients: {status['summary']['total_patients']}")
        print(f"  Idle Doctors: {status['summary']['total_idle_doctors']}")
        print(f"  Active Doctors: {status['summary']['total_active_doctors']}")
        print(f"\nDepartment Details:")
        for dept_id, dept_status in status["departments"].items():
            print(f"\n  {dept_status['name']} ({dept_id}):")
            print(
                f"    Emergency Queue: {dept_status['queue_lengths']['emergency_queue']} patients"
            )
            print(
                f"    Walk-in Queue: {dept_status['queue_lengths']['walk_in_queue']} patients"
            )
            print(
                f"    Priority Queue: {dept_status['queue_lengths']['priority_queue']} patients"
            )
            print(f"    Doctors: {len(dept_status['doctors'])}")
            for doc in dept_status["doctors"]:
                status_str = (
                    "IDLE"
                    if doc["is_idle"]
                    else f"BUSY with {doc['current_patient']['name']}"
                )
                doctor_display_name = doc["doctor_name"]
                if not doctor_display_name.startswith("Dr."):
                    doctor_display_name = f"Dr. {doctor_display_name}"
                print(f"      - {doctor_display_name}: {status_str}")
        print("\n" + "=" * 60)

    def check_in_patient(
        self, patient_id, dept_id, danger_level=3, doctor_id=None, current_time=None
    ):
        """
        Check in a patient to the hospital triage system.

        Priority 1 (Critical): Add to emergency queue, print warning, return immediately
        Priority 2 (Booked): Verify appointment with doctor, add to booked queue.
                            If late (>15 min), demote to walk-in (Priority 3)
        Priority 3 (Walk-in): Generate ticket W-001, W-002 etc., add to walk-in queue

        If patient doesn't exist, auto-create with minimal info.
        """
        # Auto-create patient if doesn't exist
        if patient_id not in self.patients:
            self.patients[patient_id] = Patient(
                patient_id=patient_id, name="", danger_level=danger_level
            )

        patient = self.patients[patient_id]
        patient.danger_level = danger_level

        # Auto-create department if doesn't exist
        if dept_id not in self.departments:
            self.departments[dept_id] = Department(dept_id, f"Dept_{dept_id}")

        department = self.departments[dept_id]

        # Priority 1: Critical - add to emergency queue
        if danger_level == 1:
            patient.ticket_number = "EMERGENCY"
            department.emergency_queue.append(patient_id)
            print(
                f"WARNING: Critical patient {patient_id} checked in to {dept_id} - IMMEDIATE ATTENTION REQUIRED"
            )
            return {
                "status": "checked_in",
                "priority": 1,
                "queue": "emergency",
                "ticket": patient.ticket_number,
                "department": dept_id,
            }

        # Priority 2: Booked - verify appointment and add to doctor's booked queue
        if danger_level == 2:
            if not doctor_id:
                return {
                    "status": "error",
                    "message": "doctor_id required for booked patients",
                }

            # Check if doctor exists
            if doctor_id not in self.doctors:
                # Demote to walk-in if doctor not found
                danger_level = 3
                patient.danger_level = 3
            else:
                doctor = self.doctors[doctor_id]

                # Verify patient has appointment with this doctor
                has_appointment = patient.is_booked and patient.doctor_id == doctor_id

                if not has_appointment:
                    # No valid appointment - demote to walk-in
                    danger_level = 3
                    patient.danger_level = 3
                else:
                    # Check if patient is late (>15 minutes past appointment time)
                    is_late = False
                    if patient.appointment_time and current_time:
                        from datetime import datetime, timedelta

                        time_diff = current_time - patient.appointment_time
                        if time_diff > timedelta(minutes=15):
                            is_late = True

                    if is_late:
                        # Demote to walk-in
                        danger_level = 3
                        patient.danger_level = 3
                        patient.is_booked = False
                    else:
                        # Valid booked appointment - add to doctor's queue
                        ticket = self._get_next_booked_ticket()
                        patient.ticket_number = ticket
                        doctor.booked_queue.append(patient_id)
                        return {
                            "status": "checked_in",
                            "priority": 2,
                            "queue": f"booked_doctor_{doctor_id}",
                            "ticket": ticket,
                            "department": dept_id,
                            "doctor": doctor_id,
                        }

        # Priority 3: Walk-in
        if danger_level == 3:
            self.walk_in_counter += 1
            ticket = f"W-{self.walk_in_counter:03d}"
            patient.ticket_number = ticket
            department.walk_in_queue.append(patient_id)
            return {
                "status": "checked_in",
                "priority": 3,
                "queue": "walk_in",
                "ticket": ticket,
                "department": dept_id,
            }

        return {"status": "error", "message": f"Invalid danger_level: {danger_level}"}

    def get_queue_status(self, dept_id):
        """
        Return status of all queues in a department.
        Includes emergency, walk-in, and per-doctor booked queues.
        """
        if dept_id not in self.departments:
            return {"status": "error", "message": f"Department {dept_id} not found"}

        department = self.departments[dept_id]

        # Get doctor queues for this department
        doctor_queues = {}
        for doc_id in department.doctor_ids:
            if doc_id in self.doctors:
                doctor = self.doctors[doc_id]
                doctor_queues[doc_id] = {
                    "queue": list(doctor.booked_queue),
                    "current_patient": doctor.current_patient_id,
                    "queue_length": len(doctor.booked_queue),
                }

        return {
            "status": "success",
            "department": dept_id,
            "emergency": {
                "queue": list(department.emergency_queue),
                "queue_length": len(department.emergency_queue),
                "next_patient": department.emergency_queue[0]
                if department.emergency_queue
                else None,
            },
            "walk_in": {
                "queue": list(department.walk_in_queue),
                "queue_length": len(department.walk_in_queue),
                "next_patient": department.walk_in_queue[0]
                if department.walk_in_queue
                else None,
            },
            "doctor_queues": doctor_queues,
            "total_waiting": (
                len(department.emergency_queue)
                + len(department.walk_in_queue)
                + sum(dq["queue_length"] for dq in doctor_queues.values())
            ),
        }

    def get_patient_ticket(self, patient_id):
        """
        Return patient's ticket number and priority level.
        """
        if patient_id not in self.patients:
            return {"status": "error", "message": f"Patient {patient_id} not found"}

        patient = self.patients[patient_id]
        priority_name = {1: "Critical", 2: "Booked", 3: "Walk-in"}.get(
            patient.danger_level, "Unknown"
        )

        return {
            "status": "success",
            "patient_id": patient_id,
            "ticket_number": patient.ticket_number,
            "priority_level": patient.danger_level,
            "priority_name": priority_name,
        }


# Example usage / test
if __name__ == "__main__":
    from datetime import datetime, timedelta

    ts = TriageSystem()

    # Setup: Create departments and doctors
    ts.departments["DEPT01"] = Department("DEPT01", "Emergency")
    ts.departments["DEPT02"] = Department("DEPT02", "Cardiology")
    ts.doctors["D001"] = Doctor("D001", "Dr. Smith", "DEPT01")
    ts.doctors["D002"] = Doctor("D002", "Dr. Jones", "DEPT02")
    ts.departments["DEPT01"].doctor_ids = {"D001"}
    ts.departments["DEPT02"].doctor_ids = {"D002"}

    print("=" * 60)
    print("TEST 1: Critical Patient (Priority 1)")
    result = ts.check_in_patient("P001", "DEPT01", danger_level=1)
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("TEST 2: Booked Patient - On Time (Priority 2)")
    # Create patient with appointment
    ts.patients["P002"] = Patient(
        "P002", "Alice", 30, "Headache", danger_level=2, is_booked=True
    )
    ts.patients["P002"].doctor_id = "D001"
    ts.patients["P002"].appointment_time = datetime.now()
    result = ts.check_in_patient(
        "P002", "DEPT01", danger_level=2, doctor_id="D001", current_time=datetime.now()
    )
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("TEST 3: Booked Patient - Late (Demoted to Priority 3)")
    ts.patients["P003"] = Patient(
        "P003", "Bob", 45, "Fever", danger_level=2, is_booked=True
    )
    ts.patients["P003"].doctor_id = "D001"
    ts.patients["P003"].appointment_time = datetime.now() - timedelta(minutes=30)
    result = ts.check_in_patient(
        "P003", "DEPT01", danger_level=2, doctor_id="D001", current_time=datetime.now()
    )
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("TEST 4: Walk-in Patient (Priority 3)")
    result = ts.check_in_patient("P004", "DEPT01", danger_level=3)
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("TEST 5: Auto-created Patient (doesn't exist)")
    result = ts.check_in_patient("P999", "DEPT02", danger_level=3)
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("QUEUE STATUS FOR DEPT01:")
    status = ts.get_queue_status("DEPT01")
    print(f"Emergency queue: {status['emergency']}")
    print(f"Walk-in queue: {status['walk_in']}")
    print(f"Doctor queues: {status['doctor_queues']}")
    print(f"Total waiting: {status['total_waiting']}")

    print("\n" + "=" * 60)
    print("PATIENT TICKETS:")
    for pid in ["P001", "P002", "P003", "P004", "P999"]:
        ticket_info = ts.get_patient_ticket(pid)
        print(f"{pid}: {ticket_info}")

    # Existing functionality tests
    print("\n" + "=" * 60)
    print("EXISTING FUNCTIONALITY TESTS:")
    p1_data = {"patient_id": "P005", "name": "Charlie", "age": 25, "symptoms": "Cough"}
    print(ts.book_appointment(p1_data, "2026-05-22", "09:00-10:00", "D001"))
    print(ts.get_available_slots("2026-05-22", "D001"))
    print(ts.get_doctor_appointments("D001", "2026-05-22"))

    # NEW METHOD TESTS
    print("\n" + "=" * 60)
    print("NEW METHOD TESTS:")

    # Clear previous state to make tests clearer
    ts = TriageSystem()
    ts.departments["DEPT01"] = Department("DEPT01", "Emergency")
    ts.departments["DEPT02"] = Department("DEPT02", "Cardiology")
    ts.doctors["D001"] = Doctor("D001", "Smith", "DEPT01")
    ts.doctors["D002"] = Doctor("D002", "Jones", "DEPT02")
    ts.departments["DEPT01"].doctor_ids = {"D001"}
    ts.departments["DEPT02"].doctor_ids = {"D002"}

    # Test next_patient_for_doctor
    print("\nTest 1: next_patient_for_doctor")
    # Create emergency patient
    p_emergency = Patient(
        "P006", "Emergency Patient", 40, "Heart Attack", danger_level=1
    )
    p_emergency.ticket_number = "E-001"
    ts.add_to_emergency_queue("DEPT01", p_emergency)

    # Create walk-in patient
    p_walkin = Patient("P007", "Walk-in Patient", 30, "Flu", danger_level=3)
    p_walkin.ticket_number = "W-001"
    ts.add_to_walk_in_queue("DEPT01", p_walkin)

    # Create booked patient with valid appointment time
    p_booked = Patient(
        "P008", "Booked Patient", 35, "Checkup", danger_level=2, is_booked=True
    )
    p_booked.ticket_number = "B-001"
    appt_time = datetime.now()
    ts.add_to_booked_queue("D001", p_booked, appt_time)

    # Should get emergency patient first (Priority 1)
    next_p = ts.next_patient_for_doctor("D001")
    print(
        f"Next patient for D001: {next_p.name if next_p else 'None'} (Expected: Emergency Patient)"
    )

    # Test complete_examination - should get booked patient next (Priority 2, within 15 min)
    print("\nTest 2: complete_examination")
    next_p = ts.complete_examination("D001")

    # Test get_doctor_status
    print("\nTest 3: get_doctor_status")
    status = ts.get_doctor_status("D001")
    print(f"Doctor status: {status}")

    # Test get_all_departments_status
    print("\nTest 4: get_all_departments_status")
    all_status = ts.get_all_departments_status()
    print(f"All departments status summary: {all_status['summary']}")

    # Test promote_waited_patients
    print("\nTest 5: promote_waited_patients")
    # Create walk-in patient who has been waiting long time
    p_long_wait = Patient("P009", "Long Wait Patient", 50, "Back Pain", danger_level=3)
    p_long_wait.ticket_number = "W-002"
    ts.add_to_walk_in_queue("DEPT01", p_long_wait)
    # Simulate long wait by backdating wait_start_time
    p_long_wait.wait_start_time = datetime.now() - timedelta(minutes=130)

    promoted = ts.promote_waited_patients("DEPT01", max_wait_minutes=120)
    print(f"Promoted {len(promoted)} patients")

    # Print final system status
    print("\n" + "=" * 60)
    print("FINAL SYSTEM STATUS:")
    ts.print_system_status()
