from flask import request, render_template, redirect, url_for, session, flash
from flask import Flask
from database import get_db_connection
from routes.auth import auth
from datetime import datetime, date
import calendar
import os
import uuid
from werkzeug.utils import secure_filename
from services.email_service import send_email

app = Flask(__name__)

# Resource image upload configuration
UPLOAD_FOLDER = os.path.join(
    app.root_path, "static", "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


app.secret_key = "change-this-to-a-random-secret"

app.register_blueprint(auth)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()
    student_id = session["student_id"]

    # 1. Count resources listed by the student
    my_resources = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM resources
        WHERE student_id = ?
        """,
        (student_id,)
    ).fetchone()["total"]

    # 2. Count bookings made by the student
    my_bookings = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM bookings
        WHERE borrower_id = ?
        """,
        (student_id,)
    ).fetchone()["total"]

    # 3. Count pending requests received
    pending_requests = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM bookings b
        JOIN resources r ON b.resource_id = r.id
        WHERE r.student_id = ?
        AND b.status = 'Pending'
        """,
        (student_id,)
    ).fetchone()["total"]

    # 4. Recent bookings made by the student
    recent_bookings = connection.execute(
        """
        SELECT
            b.id,
            r.title AS resource_title,
            s.name AS other_student,
            b.start_date,
            b.end_date,
            b.total_price,
            b.status
        FROM bookings b
        JOIN resources r ON b.resource_id = r.id
        JOIN students s ON r.student_id = s.id
        WHERE b.borrower_id = ?
        ORDER BY b.id DESC
        LIMIT 5
        """,
        (student_id,)
    ).fetchall()

    # 5. Recent requests received for the student's resources
    received_requests = connection.execute(
        """
        SELECT
            b.id,
            r.title AS resource_title,
            s.name AS other_student,
            b.start_date,
            b.end_date,
            b.total_price,
            b.status
        FROM bookings b
        JOIN resources r ON b.resource_id = r.id
        JOIN students s ON b.borrower_id = s.id
        WHERE r.student_id = ?
        ORDER BY b.id DESC
        LIMIT 5
        """,
        (student_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        student_name=session["student_name"],
        my_resources=my_resources,
        my_bookings=my_bookings,
        pending_requests=pending_requests,
        recent_bookings=recent_bookings,
        received_requests=received_requests
    )


@app.route("/add-resource", methods=["GET", "POST"])
def add_resource():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        condition = request.form["condition"]
        rental_price = request.form["rental_price"]

        # Get uploaded image
        image = request.files.get("resource_image")
        image_filename = None

        if image and image.filename:

            if not allowed_file(image.filename):
                flash("Please upload a JPG, JPEG, PNG or WEBP image.")
                return redirect(url_for("add_resource"))

            # Check image size
            image.seek(0, os.SEEK_END)
            file_size = image.tell()
            image.seek(0)

            if file_size > 5 * 1024 * 1024:
                flash("Image must be smaller than 5 MB.")
                return redirect(url_for("add_resource"))

            # Generate unique filename
            extension = image.filename.rsplit(".", 1)[1].lower()
            image_filename = f"{uuid.uuid4().hex}.{extension}"

            # Save image in uploads folder
            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    image_filename
                )
            )

        # Save resource details in database
        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO resources
            (
                student_id,
                title,
                description,
                category,
                condition,
                rental_price,
                image_filename
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["student_id"],
                title,
                description,
                category,
                condition,
                rental_price,
                image_filename
            )
        )

        connection.commit()
        connection.close()

        flash("Resource added successfully!")
        return redirect(url_for("dashboard"))

    return render_template("add_resource.html")


@app.route("/delete-resource/<int:resource_id>", methods=["POST"])
def delete_resource(resource_id):

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()
    image_filename = None

    try:
        # Find the resource owned by the logged-in student
        resource = connection.execute(
            """
            SELECT id, image_filename
            FROM resources
            WHERE id = ? AND student_id = ?
            """,
            (resource_id, session["student_id"])
        ).fetchone()

        if resource is None:
            flash("Resource not found or you are not authorized to delete it.")
            return redirect(url_for("browse_resources"))

        # Preserve booking history
        booking = connection.execute(
            """
            SELECT id
            FROM bookings
            WHERE resource_id = ?
            LIMIT 1
            """,
            (resource_id,)
        ).fetchone()

        if booking:
            flash(
                "This resource cannot be deleted because it has booking history."
            )
            return redirect(url_for("browse_resources"))

        image_filename = resource["image_filename"]

        # Delete the resource from the database
        connection.execute(
            """
            DELETE FROM resources
            WHERE id = ? AND student_id = ?
            """,
            (resource_id, session["student_id"])
        )

        connection.commit()

        # Delete the uploaded image only after successful database deletion
        if image_filename:
            upload_folder = os.path.realpath(
                app.config["UPLOAD_FOLDER"]
            )

            image_path = os.path.realpath(
                os.path.join(upload_folder, image_filename)
            )

            if (
                os.path.commonpath([upload_folder, image_path])
                == upload_folder
                and os.path.isfile(image_path)
            ):
                os.remove(image_path)

        flash("Your resource has been deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Resource deletion error:", error)
        flash("Something went wrong while deleting the resource.")

    finally:
        connection.close()

    return redirect(url_for("browse_resources"))


@app.route("/resources")
def browse_resources():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    resources = connection.execute(
        """
        SELECT resources.*, students.name AS owner_name
        FROM resources
        JOIN students
        ON resources.student_id = students.id
        WHERE resources.availability = 'Available'
        ORDER BY resources.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "resources.html",
        resources=resources,
        today=date.today().isoformat()
    )

@app.route("/resource/<int:resource_id>")
def resource_details(resource_id):

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    resource = connection.execute(
        """
        SELECT
            resources.*,
            students.name AS owner_name
        FROM resources
        JOIN students
            ON resources.student_id = students.id
        WHERE resources.id = ?
        AND resources.availability = 'Available'
        """,
        (resource_id,)
    ).fetchone()

    connection.close()

    if resource is None:
        flash("Resource not found or unavailable.")
        return redirect(url_for("browse_resources"))

    if resource["student_id"] == session["student_id"]:
        flash("This is your own resource.")
        return redirect(url_for("browse_resources"))

    return render_template(
        "resource_details.html",
        resource=resource,
        today=date.today().isoformat()
    )


@app.route("/book/<int:resource_id>", methods=["POST"])
def book_resource(resource_id):

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    # Validate submitted dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

    except (ValueError, TypeError):
        flash("Please select valid rental dates.")
        return redirect(
            url_for("resource_details", resource_id=resource_id)
        )

    today = date.today()

    if start < today:
        flash("Start date cannot be in the past.")
        return redirect(
            url_for("resource_details", resource_id=resource_id)
        )

    if end < start:
        flash("End date cannot be before start date.")
        return redirect(
            url_for("resource_details", resource_id=resource_id)
        )

    # Maximum rental period: one calendar month
    target_month = start.month % 12 + 1
    target_year = start.year + (1 if start.month == 12 else 0)

    last_day = calendar.monthrange(target_year, target_month)[1]

    max_end_date = date(
        target_year,
        target_month,
        min(start.day, last_day)
    )

    if end > max_end_date:
        flash("Rental period cannot exceed one calendar month.")
        return redirect(
            url_for("resource_details", resource_id=resource_id)
        )

    connection = get_db_connection()

    try:
        resource = connection.execute(
            "SELECT * FROM resources WHERE id = ?",
            (resource_id,)
        ).fetchone()

        if resource is None:
            flash("Resource not found.")
            return redirect(url_for("browse_resources"))

        if resource["student_id"] == session["student_id"]:
            flash("You cannot book your own resource.")
            return redirect(url_for("browse_resources"))

        if resource["availability"] != "Available":
            flash("This resource is not available.")
            return redirect(url_for("browse_resources"))

        # Calculate inclusive rental days
        total_days = (end - start).days + 1

        total_price = total_days * resource["rental_price"]

        connection.execute(
            """
            INSERT INTO bookings
            (resource_id, borrower_id, start_date, end_date, total_price)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                resource_id,
                session["student_id"],
                start_date,
                end_date,
                total_price
            )
        )

        connection.commit()

        flash(
            f"Booking request submitted! Total: ₹{total_price:.2f}"
        )

    except Exception as error:
        connection.rollback()

        print("Booking error:", error)

        flash("Something went wrong while submitting your booking.")

    finally:
        connection.close()

    return redirect(url_for("browse_resources"))

@app.route("/my-bookings")
def my_bookings():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    bookings = connection.execute(
        """
        SELECT
            bookings.*,
            resources.title AS resource_title,
            resources.category,
            students.name AS owner_name
        FROM bookings
        JOIN resources
            ON bookings.resource_id = resources.id
        JOIN students
            ON resources.student_id = students.id
        WHERE bookings.borrower_id = ?
        ORDER BY bookings.id DESC
        """,
        (session["student_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )


@app.route("/booking-requests")
def booking_requests():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    requests = connection.execute(
        """
        SELECT
            bookings.*,
            resources.title AS resource_title,
            students.name AS borrower_name,
            students.email AS borrower_email
        FROM bookings
        JOIN resources
            ON bookings.resource_id = resources.id
        JOIN students
            ON bookings.borrower_id = students.id
        WHERE resources.student_id = ?
        ORDER BY bookings.id DESC
        """,
        (session["student_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "booking_requests.html",
        requests=requests
    )


@app.route("/update-booking/<int:booking_id>", methods=["POST"])
def update_booking(booking_id):

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    action = request.form.get("action")

    if action not in ["Accepted", "Rejected"]:
        flash("Invalid booking action.")
        return redirect(url_for("booking_requests"))

    connection = get_db_connection()

    booking = connection.execute(
        """
        SELECT bookings.id
        FROM bookings
        JOIN resources
            ON bookings.resource_id = resources.id
        WHERE bookings.id = ?
        AND resources.student_id = ?
        AND bookings.status = 'Pending'
        """,
        (booking_id, session["student_id"])
    ).fetchone()

    if booking is None:
        connection.close()

        flash("Booking request not found or already processed.")

        return redirect(url_for("booking_requests"))

    # Check for overlapping accepted bookings
    if action == "Accepted":

        conflict = connection.execute(
            """
            SELECT id
            FROM bookings
            WHERE resource_id = (
                SELECT resource_id
                FROM bookings
                WHERE id = ?
            )
            AND id != ?
            AND status = 'Accepted'
            AND start_date <= (
                SELECT end_date
                FROM bookings
                WHERE id = ?
            )
            AND end_date >= (
                SELECT start_date
                FROM bookings
                WHERE id = ?
            )
            """,
            (booking_id, booking_id, booking_id, booking_id)
        ).fetchone()

        if conflict:
            connection.close()

            flash(
                "This resource is already booked for overlapping dates."
            )

            return redirect(url_for("booking_requests"))

    # Update booking status
    connection.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        (action, booking_id)
    )

    connection.commit()
    connection.close()

    flash(f"Booking request {action.lower()} successfully!")

    return redirect(url_for("booking_requests"))

@app.route("/post-room", methods=["GET", "POST"])
def post_room():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        listing_type = request.form.get("listing_type")
        room_type = request.form.get("room_type")
        location = request.form.get("location", "").strip()
        gender_preference = request.form.get(
            "gender_preference", "Any"
        )
        available_from = request.form.get("available_from")
        facilities = ", ".join(
            request.form.getlist("facilities")
        )

        # Validate required text fields
        if not all([
            title,
            description,
            location,
            available_from
        ]):
            flash("Please fill in all required fields.")
            return redirect(url_for("post_room"))

        # Validate listing type
        if listing_type not in ["Entire Room", "Vacant Bed"]:
            flash("Please select a valid listing type.")
            return redirect(url_for("post_room"))

        if room_type not in ["Single", "Shared"]:
            flash("Please select a valid room type.")
            return redirect(url_for("post_room"))

        if gender_preference not in ["Any", "Male", "Female"]:
            flash("Please select a valid gender preference.")
            return redirect(url_for("post_room"))

        # Validate rent and available beds
        try:
            monthly_rent = float(
                request.form.get("monthly_rent", "")
            )

            available_beds = int(
                request.form.get("available_beds", "")
            )

            if monthly_rent <= 0 or available_beds < 1:
                raise ValueError

        except (ValueError, TypeError):
            flash(
                "Enter a valid monthly rent and number of available beds."
            )
            return redirect(url_for("post_room"))

        # Validate available date
        try:
            available_date = datetime.strptime(
                available_from, "%Y-%m-%d"
            ).date()

            if available_date < date.today():
                flash("Availability date cannot be in the past.")
                return redirect(url_for("post_room"))

        except (ValueError, TypeError):
            flash("Please select a valid availability date.")
            return redirect(url_for("post_room"))

        # Get uploaded images
        images = [
            image
            for image in request.files.getlist("room_images")
            if image and image.filename
        ]

        if not 2 <= len(images) <= 5:
            flash(
                "Please upload at least 2 and at most 5 room photos."
            )
            return redirect(url_for("post_room"))

        saved_files = []
        connection = None

        try:
            # Validate every image before saving
            for image in images:

                if not allowed_file(image.filename):
                    raise ValueError(
                        "Only JPG, JPEG, PNG and WEBP images are allowed."
                    )

                image.seek(0, os.SEEK_END)
                file_size = image.tell()
                image.seek(0)

                if file_size > 5 * 1024 * 1024:
                    raise ValueError(
                        "Each image must be smaller than 5 MB."
                    )

            # Save images with unique filenames
            for image in images:

                extension = image.filename.rsplit(".", 1)[1].lower()

                image_filename = (
                    f"{uuid.uuid4().hex}.{extension}"
                )

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )
                )

                saved_files.append(image_filename)

            connection = get_db_connection()

            # Save room details
            cursor = connection.execute(
                """
                INSERT INTO room_listings
                (
                    student_id,
                    title,
                    description,
                    listing_type,
                    room_type,
                    location,
                    monthly_rent,
                    available_beds,
                    gender_preference,
                    facilities,
                    available_from
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["student_id"],
                    title,
                    description,
                    listing_type,
                    room_type,
                    location,
                    monthly_rent,
                    available_beds,
                    gender_preference,
                    facilities,
                    available_from
                )
            )

            room_id = cursor.lastrowid

            # Save all image records
            for filename in saved_files:

                connection.execute(
                    """
                    INSERT INTO room_images
                    (room_listing_id, image_filename)
                    VALUES (?, ?)
                    """,
                    (room_id, filename)
                )

            connection.commit()

            flash(
                "Your room listing has been published successfully!"
            )

            return redirect(url_for("dashboard"))

        except ValueError as error:

            if connection:
                connection.rollback()

            flash(str(error))

            return redirect(url_for("post_room"))

        except Exception as error:

            if connection:
                connection.rollback()

            print("Room listing error:", error)

            flash(
                "Something went wrong while publishing your room."
            )

            return redirect(url_for("post_room"))

        finally:

            if connection:
                connection.close()

    return render_template("post_room.html")


@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out successfully.")

    return redirect(url_for("auth.login"))


@app.route("/my-room-listings")
def my_room_listings():

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    try:
        listings = connection.execute(
            """
            SELECT *
            FROM room_listings
            WHERE student_id = ?
            ORDER BY id DESC
            """,
            (session["student_id"],)
        ).fetchall()

        my_listings = []

        for listing in listings:
            listing_data = dict(listing)

            images = connection.execute(
                """
                SELECT image_filename
                FROM room_images
                WHERE room_listing_id = ?
                """,
                (listing["id"],)
            ).fetchall()

            listing_data["images"] = [
                image["image_filename"] for image in images
            ]

            my_listings.append(listing_data)

        return render_template(
            "my_room_listings.html",
            listings=my_listings
        )

    finally:
        connection.close()


@app.route("/delete-room-listing/<int:listing_id>", methods=["POST"])
def delete_room_listing(listing_id):

    if "student_id" not in session:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    try:
        # Verify that this listing belongs to the logged-in student
        listing = connection.execute(
            """
            SELECT id
            FROM room_listings
            WHERE id = ? AND student_id = ?
            """,
            (listing_id, session["student_id"])
        ).fetchone()

        if listing is None:
            flash("Room listing not found or you are not authorized.")
            return redirect(url_for("my_room_listings"))

        # Collect image filenames before deleting database records
        images = connection.execute(
            """
            SELECT image_filename
            FROM room_images
            WHERE room_listing_id = ?
            """,
            (listing_id,)
        ).fetchall()

        image_filenames = [
            image["image_filename"] for image in images
        ]

        # Delete the listing. Related room_images records
        # are deleted automatically because of ON DELETE CASCADE.
        connection.execute(
            """
            DELETE FROM room_listings
            WHERE id = ? AND student_id = ?
            """,
            (listing_id, session["student_id"])
        )

        connection.commit()

        # Remove uploaded image files after successful DB deletion
        upload_folder = os.path.realpath(
            app.config["UPLOAD_FOLDER"]
        )

        for filename in image_filenames:

            image_path = os.path.realpath(
                os.path.join(upload_folder, filename)
            )

            if (
                os.path.commonpath([upload_folder, image_path])
                == upload_folder
                and os.path.isfile(image_path)
            ):
                os.remove(image_path)

        flash("Your room listing has been deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Room deletion error:", error)
        flash("Something went wrong while deleting the room listing.")

    finally:
        connection.close()

    return redirect(url_for("my_room_listings"))


if __name__ == "__main__":
    app.run(debug=True)
