"""
Constants and validation rules for AASTU Colleges, Departments, Batches,
Fellowship Teams, and Football Positions.
"""

COLLEGE_CHOICES = [
    ('ENGINEERING', 'College of Engineering'),
    ('APPLIED_SCIENCES', 'College of Applied Sciences'),
    ('OTHER', 'Other'),
]

ENGINEERING_DEPARTMENTS = [
    ('Software Engineering', 'Software Engineering'),
    ('Mechanical Engineering', 'Mechanical Engineering'),
    ('Electrical Engineering', 'Electrical Engineering'),
    ('Electromechanical Engineering', 'Electromechanical Engineering'),
    ('Civil Engineering', 'Civil Engineering'),
    ('Environmental Engineering', 'Environmental Engineering'),
    ('Chemical Engineering', 'Chemical Engineering'),
    ('Mining Engineering', 'Mining Engineering'),
    ('Architecture', 'Architecture'),
]

APPLIED_SCIENCES_DEPARTMENTS = [
    ('Food Science', 'Food Science'),
    ('Biotechnology', 'Biotechnology'),
    ('Geology', 'Geology'),
    ('Industrial Engineering', 'Industrial Engineering'),
]

OTHER_DEPARTMENTS = [
    ('Other', 'Other'),
]

ALL_DEPARTMENTS = ENGINEERING_DEPARTMENTS + APPLIED_SCIENCES_DEPARTMENTS + OTHER_DEPARTMENTS

ENGINEERING_YEARS = [
    ('1st Year', '1st Year'),
    ('2nd Year', '2nd Year'),
    ('3rd Year', '3rd Year'),
    ('4th Year', '4th Year'),
    ('5th Year', '5th Year'),
    ('Other', 'Other'),
]

APPLIED_SCIENCES_YEARS = [
    ('1st Year', '1st Year'),
    ('2nd Year', '2nd Year'),
    ('3rd Year', '3rd Year'),
    ('4th Year', '4th Year'),
    ('Other', 'Other'),
]

OTHER_YEARS = [
    ('Other', 'Other'),
]

ALL_YEARS = [
    ('1st Year', '1st Year'),
    ('2nd Year', '2nd Year'),
    ('3rd Year', '3rd Year'),
    ('4th Year', '4th Year'),
    ('5th Year', '5th Year'),
    ('Other', 'Other'),
]

FELLOWSHIP_TEAMS = [
    ('Ebenezer', 'Ebenezer'),
    ('BS Team', 'BS Team'),
    ('Lady', 'Lady'),
    ('Elios', 'Elios'),
    ('Media', 'Media'),
    ('Nathanism', 'Nathanism'),
    ('Action and Prayer', 'Action and Prayer'),
]

GENDER_CHOICES = [
    ('MALE', 'Male'),
    ('FEMALE', 'Female'),
]

FOOTBALL_POSITIONS = [
    ('Goalkeeper', 'Goalkeeper'),
    ('Defender', 'Defender'),
    ('Centre Back', 'Centre Back'),
    ('Full Back', 'Full Back'),
    ('Midfielder', 'Midfielder'),
    ('Attacking Midfielder', 'Attacking Midfielder'),
    ('Winger', 'Winger'),
    ('Forward', 'Forward'),
    ('Striker', 'Striker'),
    ('Other', 'Other'),
]

COMPETING_BATCH_CHOICES = [
    ('2ND_YEAR', '2nd Year'),
    ('3RD_YEAR', '3rd Year'),
    ('4TH_YEAR', '4th Year'),
    ('5TH_YEAR', '5th Year'),
    ('OTHER', 'Other (Community Only)'),
]


def validate_academic_eligibility(college: str, department: str, academic_year: str):
    """
    Validates college, department, and academic year combinations,
    and returns competition eligibility information.

    Returns:
        tuple: (is_valid: bool, error_message: str | None, is_football_eligible: bool, competing_batch: str | None)
    """
    college_keys = [c[0] for c in COLLEGE_CHOICES]
    if college not in college_keys:
        return False, f"Invalid college '{college}'.", False, None

    # Department validation per college
    if college == 'ENGINEERING':
        valid_depts = [d[0] for d in ENGINEERING_DEPARTMENTS]
        if department not in valid_depts:
            return False, f"Department '{department}' is not valid for College of Engineering.", False, None

        valid_years = [y[0] for y in ENGINEERING_YEARS]
        if academic_year not in valid_years:
            return False, f"Academic year '{academic_year}' is not valid for College of Engineering.", False, None

    elif college == 'APPLIED_SCIENCES':
        valid_depts = [d[0] for d in APPLIED_SCIENCES_DEPARTMENTS]
        if department not in valid_depts:
            return False, f"Department '{department}' is not valid for College of Applied Sciences.", False, None

        valid_years = [y[0] for y in APPLIED_SCIENCES_YEARS]
        if academic_year not in valid_years:
            return False, f"Academic year '{academic_year}' is not valid for College of Applied Sciences (program is 4 years).", False, None

    elif college == 'OTHER':
        if department != 'Other':
            return False, "Department for 'Other' college must be 'Other'.", False, None
        if academic_year != 'Other':
            return False, "Academic year for 'Other' college must be 'Other'.", False, None

    # Check football tournament eligibility
    if academic_year == '1st Year':
        # 1st years do not participate in football so they can concentrate on academics
        return True, None, False, None

    if academic_year == 'Other' or college == 'OTHER':
        # Community-only fellowship members
        return True, None, False, None

    if college == 'APPLIED_SCIENCES' and academic_year == '5th Year':
        # Applied Sciences is a 4-year program
        return False, "Applied Sciences students cannot be in 5th Year.", False, None

    # Eligible batches
    batch_map = {
        '2nd Year': '2ND_YEAR',
        '3rd Year': '3RD_YEAR',
        '4th Year': '4TH_YEAR',
        '5th Year': '5TH_YEAR',
    }
    competing_batch = batch_map.get(academic_year)
    if competing_batch:
        return True, None, True, competing_batch

    return True, None, False, None
