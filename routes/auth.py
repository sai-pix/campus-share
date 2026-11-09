
from flask import (
    Blueprint, request, render_template,
    redirect, url_for, flash, session
)

import secrets
import hashlib
import sqlite3

from datetime import datetime, timedelta, timezone

from services.email_service import send_email
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

auth = Blueprint("auth", __name__)


# ==========================================
# REGISTER - SEND EMAIL VERIFICATION OTP
# ==========================================


@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        college_student_id = request.form.get(
            "college_student_id", ""
        ).strip()

        name = request.form.get("name", "").strip()

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        confirm_password = request.form.get("confirm_password", "")

        # Values to preserve when displaying validation errors
        form_data = {
            "college_student_id": college_student_id,
            "name": name,
            "email": email
        }

        # Validate required fields
        if not all([
            college_student_id,
            name,
            email,
            password,
            confirm_password
        ]):
            flash("Please fill in all registration fields.", "error")
            return render_template("register.html", **form_data)

        # Validate password length
        if len(password) < 8:
            flash(
                "Password must be at least 8 characters long.",
                "error"
            )
            return render_template("register.html", **form_data)

        # Confirm password
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", **form_data)

        connection = get_db_connection()

        try:

            # Check whether student ID or email already exists
            existing_student = connection.execute("""
                SELECT id FROM students
                WHERE college_student_id = ? OR email = ?
            """, (college_student_id, email)).fetchone()

            if existing_student:
                flash(
                    "College ID or email is already registered.",
                    "error"
                )
                return render_template("register.html", **form_data)

            # Generate 6-digit OTP
            otp = str(secrets.randbelow(900000) + 100000)

            otp_hash = hashlib.sha256(otp.encode()).hexdigest()

            expires_at = (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat()

            password_hash = generate_password_hash(password)

            # Remove previous pending registration using this ID or email
            connection.execute("""
                DELETE FROM registration_otps
                WHERE college_student_id = ? OR email = ?
            """, (college_student_id, email))

            # Store temporary registration details
            connection.execute("""
                INSERT INTO registration_otps
                (
                    college_student_id,
                    name,
                    email,
                    password_hash,
                    otp_hash,
                    expires_at,
                    attempts
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                college_student_id,
                name,
                email,
                password_hash,
                otp_hash,
                expires_at
            ))

            connection.commit()

            # Send verification email
            email_sent = send_email(
                email,
                "CampusShare - Email Verification OTP",
                f"""
Hello {name},

Welcome to CampusShare!

Your email verification OTP is:

{otp}

This OTP expires in 5 minutes.

You have a maximum of 5 attempts.

Do not share this OTP with anyone.

CampusShare Team
"""
            )

            if email_sent:

                session["registration_email"] = email

                flash("Verification OTP sent to your email.", "success")

                return redirect(
                    url_for("auth.verify_registration_otp")
                )

            else:

                connection.execute("""
                    DELETE FROM registration_otps
                    WHERE email = ?
                """, (email,))

                connection.commit()

                flash(
                    "Unable to send verification email. Please try again.",
                    "error"
                )

                return render_template("register.html", **form_data)

        except sqlite3.IntegrityError as e:

            connection.rollback()

            print("Registration Error:", e)

            flash(
                "College ID or email is already awaiting verification.",
                "error"
            )

            return render_template("register.html", **form_data)

        except Exception as e:

            connection.rollback()

            print("Registration Error:", e)

            flash("Something went wrong. Please try again.", "error")

            return render_template("register.html", **form_data)

        finally:

            connection.close()

    return render_template("register.html")


# ==========================================
# VERIFY REGISTRATION OTP
# ==========================================

@auth.route("/verify-registration-otp", methods=["GET", "POST"])
def verify_registration_otp():

    email = session.get("registration_email")

    if not email:
        flash("Please register first.")
        return redirect(url_for("auth.register"))

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        if not otp.isdigit() or len(otp) != 6:
            flash("Please enter a valid 6-digit OTP.")
            return redirect(url_for("auth.verify_registration_otp"))

        connection = get_db_connection()

        try:

            pending = connection.execute("""
                SELECT * FROM registration_otps
                WHERE email = ?
            """, (email,)).fetchone()

            if not pending:

                session.pop("registration_email", None)

                flash("Registration details not found. Please register again.")

                return redirect(url_for("auth.register"))

            # Check OTP expiration
            expiry = datetime.fromisoformat(pending["expires_at"])

            if expiry <= datetime.now(timezone.utc):

                connection.execute("""
                    DELETE FROM registration_otps
                    WHERE email = ?
                """, (email,))

                connection.commit()

                session.pop("registration_email", None)

                flash("OTP expired. Please register again.")

                return redirect(url_for("auth.register"))

            # Check maximum attempts
            if pending["attempts"] >= 5:

                connection.execute("""
                    DELETE FROM registration_otps
                    WHERE email = ?
                """, (email,))

                connection.commit()

                session.pop("registration_email", None)

                flash("Maximum attempts reached. Please register again.")

                return redirect(url_for("auth.register"))

            # Compare OTP hashes
            entered_hash = hashlib.sha256(otp.encode()).hexdigest()

            if entered_hash != pending["otp_hash"]:

                connection.execute("""
                    UPDATE registration_otps
                    SET attempts = attempts + 1
                    WHERE email = ?
                """, (email,))

                connection.commit()

                flash("Incorrect OTP. Please try again.")

                return redirect(
                    url_for("auth.verify_registration_otp")
                )

            # OTP correct - create verified student account
            connection.execute("""
                INSERT INTO students
                (
                    college_student_id,
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?, ?)
            """, (
                pending["college_student_id"],
                pending["name"],
                pending["email"],
                pending["password_hash"]
            ))

            # Delete temporary registration data
            connection.execute("""
                DELETE FROM registration_otps
                WHERE email = ?
            """, (email,))

            connection.commit()

            session.pop("registration_email", None)

            flash("Email verified! Your account has been created. Please log in.")

            return redirect(url_for("auth.login"))

        except sqlite3.IntegrityError as e:

            connection.rollback()

            print("Account Creation Error:", e)

            flash("College ID or email is already registered.")

            return redirect(url_for("auth.register"))

        except Exception as e:

            connection.rollback()

            print("OTP Verification Error:", e)

            flash("Something went wrong. Please try again.")

            return redirect(url_for("auth.verify_registration_otp"))

        finally:
            connection.close()

    return render_template("verify_registration_otp.html")


# ==========================================
# LOGIN
# ==========================================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()

        student = connection.execute(
            "SELECT * FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if student and check_password_hash(student["password"], password):

            session["student_id"] = student["id"]
            session["student_name"] = student["name"]

            flash("Login successful!")

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# ==========================================
# FORGOT PASSWORD - SEND OTP
# ==========================================

@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        session.pop("password_reset_student_id", None)
        session.pop("password_reset_authorized_id", None)

        connection = get_db_connection()

        student = connection.execute(
            "SELECT id, email FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        email_sent = False

        if student:

            otp = str(secrets.randbelow(900000) + 100000)

            otp_hash = hashlib.sha256(otp.encode()).hexdigest()

            expires_at = (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat()

            connection.execute("""
                INSERT OR REPLACE INTO password_resets
                (student_id, otp_hash, expires_at, attempts)
                VALUES (?, ?, ?, 0)
            """, (
                student["id"],
                otp_hash,
                expires_at
            ))

            connection.commit()

            email_sent = send_email(
                email,
                "CampusShare - Password Reset OTP",
                f"""
Hello,

Your CampusShare password reset OTP is:

{otp}

This OTP expires in 5 minutes.

Do not share this OTP with anyone.

If you did not request this, please ignore this email.

CampusShare Team
"""
            )

            if email_sent:

                session["password_reset_student_id"] = student["id"]

            else:

                connection.execute(
                    "DELETE FROM password_resets WHERE student_id = ?",
                    (student["id"],)
                )

                connection.commit()

        connection.close()

        flash(
            "If your email is registered, you will receive a password reset OTP."
        )

        if student and email_sent:
            return redirect(url_for("auth.verify_otp"))

        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


# ==========================================
# VERIFY FORGOT-PASSWORD OTP
# ==========================================

@auth.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    student_id = session.get("password_reset_student_id")

    if not student_id:

        flash("Please request a password reset first.")

        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        otp = request.form.get("otp", "").strip()

        if not otp.isdigit() or len(otp) != 6:

            flash("Please enter a valid 6-digit OTP.")

            return redirect(url_for("auth.verify_otp"))

        connection = get_db_connection()

        reset = connection.execute("""
            SELECT * FROM password_resets
            WHERE student_id = ?
        """, (student_id,)).fetchone()

        if not reset:

            connection.close()

            session.pop("password_reset_student_id", None)

            flash("OTP not found. Please request a new one.")

            return redirect(url_for("auth.forgot_password"))

        if datetime.fromisoformat(reset["expires_at"]) <= datetime.now(timezone.utc):

            connection.execute(
                "DELETE FROM password_resets WHERE student_id = ?",
                (student_id,)
            )

            connection.commit()
            connection.close()

            session.pop("password_reset_student_id", None)

            flash("OTP expired. Please request a new one.")

            return redirect(url_for("auth.forgot_password"))

        if reset["attempts"] >= 5:

            connection.execute(
                "DELETE FROM password_resets WHERE student_id = ?",
                (student_id,)
            )

            connection.commit()
            connection.close()

            session.pop("password_reset_student_id", None)

            flash("Maximum attempts reached. Please request a new OTP.")

            return redirect(url_for("auth.forgot_password"))

        entered_hash = hashlib.sha256(otp.encode()).hexdigest()

        if entered_hash != reset["otp_hash"]:

            connection.execute("""
                UPDATE password_resets
                SET attempts = attempts + 1
                WHERE student_id = ?
            """, (student_id,))

            connection.commit()
            connection.close()

            flash("Incorrect OTP. Please try again.")

            return redirect(url_for("auth.verify_otp"))

        connection.execute(
            "DELETE FROM password_resets WHERE student_id = ?",
            (student_id,)
        )

        connection.commit()
        connection.close()

        session.pop("password_reset_student_id", None)

        session["password_reset_authorized_id"] = student_id

        flash("OTP verified successfully!")

        return redirect(url_for("auth.reset_password"))

    return render_template("verify_otp.html")


# ==========================================
# RESET PASSWORD
# ==========================================

@auth.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    student_id = session.get("password_reset_authorized_id")

    if not student_id:

        flash("Please verify your OTP first.")

        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < 8:

            flash("Password must contain at least 8 characters.")

            return redirect(url_for("auth.reset_password"))

        if new_password != confirm_password:

            flash("Passwords do not match.")

            return redirect(url_for("auth.reset_password"))

        hashed_password = generate_password_hash(new_password)

        connection = get_db_connection()

        connection.execute("""
            UPDATE students
            SET password = ?
            WHERE id = ?
        """, (hashed_password, student_id))

        connection.commit()
        connection.close()

        session.pop("password_reset_authorized_id", None)

        flash("Password reset successful! Please log in.")

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")
