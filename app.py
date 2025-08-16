from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, func
from werkzeug.security import generate_password_hash, check_password_hash
from controller.forms import * 
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from datetime import datetime
from models.models import *

import json

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB & Login
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def setup_app():
    with app.app_context():
        print(">> Creating tables...")
        try:
            db.create_all()
            if not User.query.filter_by(email='admin@ezpark.com').first():
                admin = User(fullname='Admin', email='admin@ezpark.com', password=generate_password_hash('admin', method='pbkdf2:sha256'), is_admin=True)
                db.session.add(admin)
                db.session.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")
        
#@app.before_request
#def create_tables():
    
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    if current_user.is_admin:
        return redirect(url_for('dashboard_admin'))
    return redirect(url_for('dashboard_user'))

@app.route('/dashboard_user')
@login_required
def dashboard_user():
    reservations = Reservation.query.filter_by(user_id=current_user.id, status = 'A').order_by(Reservation.start_time.desc()).all()


    # Lot data for chart
    lot_data = {}
    for r in reservations:
        loc = r.spot.lot.prime_location_name
        lot_data[loc] = lot_data.get(loc, 0) + 1

    lots = ParkingLot.query.all()
    for lot in lots:
        available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        lot.available_spots = available

    return render_template('dashboard_user.html', reservations=reservations, lot_data=lot_data, lots=lots)

@app.route('/dashboard_admin', methods=['GET'])
@login_required
def dashboard_admin():
    #lots = ParkingLot.query.all()
    lots = ParkingLot.query.options(db.joinedload(ParkingLot.spots)).all()
    users = User.query.filter_by(is_admin=False).all()

    # Filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    location_id = request.args.get('location_id', type=int)

    reservations_query = Reservation.query
    if start_date:
        reservations_query = reservations_query.filter(Reservation.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        reservations_query = reservations_query.filter(Reservation.start_time <= datetime.fromisoformat(end_date))
    if location_id:
        spot_ids = [spot.id for spot in ParkingSpot.query.filter_by(lot_id=location_id).all()]
        reservations_query = reservations_query.filter(Reservation.spot_id.in_(spot_ids))

    filtered_reservations = reservations_query.all()
    
   
    lot_data = []
    print('Lots--',lots)
    for lot in lots:
        lot_data.append({
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'total_spots': ParkingSpot.query.filter_by(lot_id=lot.id).count(),
            'available_spots': ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count(),
            'occupied_spots' : ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        })

    active_reservations = (
        db.session.query(Reservation)
        .filter_by(status='A')  # 'A' for Active
        .join(ParkingSpot)
        .join(ParkingLot)
        .join(User)
        .order_by(Reservation.start_time.desc())
        .all()
    )   
    print('--',lot_data)
    overall_total = ParkingSpot.query.count()
    overall_occupied = ParkingSpot.query.filter_by(status='O').count()
    overall_available = overall_total - overall_occupied

    return render_template(
        'dashboard_admin.html',
        lots=lot_data,
        users=users,
        reservations=active_reservations,
        overall_data=json.dumps({
            'labels': ['Occupied', 'Available'],
            'data': [overall_occupied, overall_available]
        }),
        filter_params={
            'start_date': start_date or '',
            'end_date': end_date or '',
            'location_id': location_id or ''
        }
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(fullname=form.fullname.data, email=form.email.data, phone= form.phone.data, password=hashed_pw, address=form.address.data, pincode=form.address.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful, login now!')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/current_users')
@login_required
def current_users():
    reservations = Reservation.query.filter(Reservation.end_time > datetime.now()).all()
    return render_template('current_users.html', current_reservations=reservations)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.fullname = form.fullname.data
        current_user.email = form.email.data
        current_user.address = form.address.data
        current_user.pincode = form.pincode.data
        db.session.commit()
        flash('Profile updated.')
        return redirect(url_for('dashboard_user'))
    return render_template('edit_profile.html', form=form)

@app.route('/book_spot', methods=['GET', 'POST'])
@login_required
def book_spot():
    lot_id = request.args.get('lot_id') if request.method == 'GET' else request.form.get('lot_id')
    lot = ParkingLot.query.get(lot_id)
    available_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').count()

    if request.method == 'POST':
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')

        try:
            start_time = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for('book_spot', lot_id=lot.id))

        now = datetime.now()

        if start_time < now:
            flash("Start time cannot be in the past.", "danger")
            return redirect(url_for('book_spot', lot_id=lot.id))

        if end_time <= start_time:
            flash("End time must be after start time.", "danger")
            return redirect(url_for('book_spot', lot_id=lot.id))


        available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

        if not available_spot:
            flash("No available spots.", "danger")
            return redirect(url_for('dashboard_user'))

        reservation = Reservation(
            user_id=current_user.id,
            spot_id=available_spot.id,
            start_time=datetime.strptime(start_str, '%Y-%m-%dT%H:%M'),
            end_time=datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
        )

        available_spot.status = 'O'
        db.session.add(reservation)
        db.session.commit()

        flash("Spot booked successfully!", "success")
        return redirect(url_for('dashboard_user'))

    return render_template("book_spot.html", lot=lot, available_spots=available_spots)


@app.route('/release_spot/<int:reservation_id>', methods=['POST'])
@login_required
def release_spot(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash("You are not authorized to release this reservation.", "danger")
        return redirect(url_for('dashboard_user'))

    if reservation.spot.status != 'O':
        flash("This spot is already released.", "warning")
        return redirect(url_for('dashboard_user'))

    # Update spot and lot
    reservation.spot.status = 'A'
    reservation.end_time = datetime.utcnow()
    reservation.status = 'I'

    db.session.commit()
    flash("Spot released successfully.", "success")
    return redirect(url_for('dashboard_user'))

@app.route('/my_reservations')
@login_required
def my_reservations():
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.start_time.desc()).all()
    return render_template('my_reservations.html', reservations=reservations)
@app.route('/add_lot', methods=['GET', 'POST'])
@login_required
def add_lot():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    form = AddLotForm()
    if form.validate_on_submit():
        lot = ParkingLot(
            prime_location_name=form.prime_location_name.data,
            address=form.address.data,
            pin_code=form.pin_code.data,
            maximum_spots=form.maximum_spots.data
        )
        db.session.add(lot)
        db.session.commit()

        for i in range(1, form.maximum_spots.data + 1):
            spot = ParkingSpot(
                spot_number=i,
                status='A',
                lot_id=lot.id
            )
            db.session.add(spot)
        db.session.commit()

        flash('Parking Lot and Spots created.')
        return redirect(url_for('dashboard_admin'))
    return render_template('add_lot.html', form=form)
@app.route('/add_spot', methods=['GET', 'POST'])
@login_required
def add_spot():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    lots = ParkingLot.query.all()

    if request.method == 'POST':
        lot_id = request.form.get('lot_id', type=int)
        num_spots = request.form.get('num_spots', type=int)

        lot = ParkingLot.query.get(lot_id)
        if lot:
            existing_spot_count = len(lot.spots)
            for i in range(0, num_spots):
                spot = ParkingSpot(
                    spot_number=i + 1,
                    lot_id=lot.id,
                    status='A'
                )
                db.session.add(spot)
            db.session.commit()
            flash(f'{num_spots} spot(s) added to {lot.prime_location_name}.')
            return redirect(url_for('dashboard_admin'))
        else:
            flash('Selected parking lot not found.')

    return render_template('add_spot.html', lots=lots)

@app.route('/lot/update/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def update_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.prime_location_name = request.form['prime_location_name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']

        try:
            new_max_spots = int(request.form['maximum_spots'])
        except ValueError:
            flash('Maximum spots must be a valid number.', 'danger')
            return redirect(url_for('update_lot', lot_id=lot.id))

        # Safety check 1: At least 1 spot
        if new_max_spots < 1:
            flash('A parking lot must have at least 1 spot.', 'danger')
            return redirect(url_for('update_lot', lot_id=lot.id))

        # Safety check 2: Must be >= occupied spots
        occupied_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        if new_max_spots < occupied_count:
            flash(f'Cannot set maximum spots below the number of currently occupied spots ({occupied_count}).', 'danger')
            return redirect(url_for('update_lot', lot_id=lot.id))

        old_max_spots = lot.maximum_spots
        lot.maximum_spots = new_max_spots
        db.session.commit()  # save lot details first

        current_spot_count = ParkingSpot.query.filter_by(lot_id=lot.id).count()

        # Add spots if new max is higher
        if new_max_spots > current_spot_count:
            
            spots_to_add = new_max_spots - current_spot_count
            # Get the highest current spot_number in this lot
            last_spot_number = (
                db.session.query(func.max(ParkingSpot.spot_number))
                .filter_by(lot_id=lot.id)
                .scalar()
            ) or 0
            print('last_spot_number-->',last_spot_number)
            for i in range(spots_to_add):
                new_spot = ParkingSpot(
                    lot_id=lot.id,
                    spot_number=last_spot_number + i + 1,  # sequential numbering
                    status='A'
                )
                db.session.add(new_spot)
            db.session.commit()

        # Remove available spots if new max is smaller
        elif new_max_spots < current_spot_count:
            spots_to_remove = current_spot_count - new_max_spots
            removable_spots = (
                ParkingSpot.query
                .filter_by(lot_id=lot.id, status='A')
                .order_by(ParkingSpot.id.desc())
                .limit(spots_to_remove)
                .all()
            )
            for spot in removable_spots:
                db.session.delete(spot)
            db.session.commit()

        flash('Parking lot and spots updated successfully!', 'success')
        return redirect(url_for('dashboard_admin'))

    return render_template('update_lot.html', lot=lot)

@app.route('/lot/delete/<int:lot_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()

    if request.method == 'POST':
        if occupied_spots > 0:
            flash('Cannot delete the lot. Some spots are currently occupied.', 'danger')
            return redirect(url_for('dashboard_admin'))

        ParkingSpot.query.filter_by(lot_id=lot.id).delete()
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted successfully.', 'success')
        return redirect(url_for('dashboard_admin'))

    return render_template('delete_lot.html', lot=lot)

@app.route('/admin/lot/<int:lot_id>/spots')
@admin_required
def view_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('view_spots.html', lot=lot, spots=spots)

from sqlalchemy import func

@app.route('/view_users')
@admin_required
def view_users():
    users = (
        db.session.query(User)
        .filter_by(is_admin=False)
        .all()
    )

    user_data = []
    for user in users:
        last_reservation = (
            db.session.query(func.max(Reservation.start_time))
            .filter_by(user_id=user.id)
            .scalar()
        )
        user_data.append({
            'user': user,
            'last_booked': last_reservation
        })

    return render_template('view_users.html', user_data=user_data)

@app.route('/parking_statistics')
@login_required
def parking_statistics():
    if not current_user.is_admin:
        return redirect(url_for('dashboard_user'))

    current_year = datetime.now().year

    # === Yearly Parking Per Lot (Last 4 years) ===
    lot_names = db.session.query(ParkingLot.prime_location_name).all()
    lot_names = [name[0] for name in lot_names]
    current_year = datetime.now().year
    years = list(range(current_year - 3, current_year + 1))  # e.g., [2022, 2023, 2024, 2025]

    yearly_data = {}
    for lot in lot_names:
        yearly_data[lot] = []
        for year in years:
            count = db.session.query(func.count(Reservation.id))\
                .join(ParkingSpot).join(ParkingLot)\
                .filter(ParkingLot.prime_location_name == lot)\
                .filter(extract('year', Reservation.start_time) == year)\
                .scalar()
            yearly_data[lot].append(count)

    # === Parking by Time of Day ===
    time_labels = ["Morning", "Afternoon", "Evening", "Night"]
    time_ranges = {
        "Morning": (5, 12),
        "Afternoon": (12, 17),
        "Evening": (17, 21),
        "Night": (21, 5)
    }
    time_of_day_data = {}
    for label, (start_hour, end_hour) in time_ranges.items():
        if start_hour < end_hour:
            count = db.session.query(func.count(Reservation.id))\
                .filter(extract('hour', Reservation.start_time) >= start_hour)\
                .filter(extract('hour', Reservation.start_time) < end_hour)\
                .scalar()
        else:
            count = db.session.query(func.count(Reservation.id))\
                .filter(
                    (extract('hour', Reservation.start_time) >= start_hour) |
                    (extract('hour', Reservation.start_time) < end_hour)
                ).scalar()
        time_of_day_data[label] = count

    # === Parking by Month (Current Year) ===
    monthly_data = []
    for month in range(1, 13):
        count = db.session.query(func.count(Reservation.id))\
            .filter(extract('year', Reservation.start_time) == current_year)\
            .filter(extract('month', Reservation.start_time) == month)\
            .scalar()
        monthly_data.append(count)

    return render_template("parking_statistics.html",
                           yearly_data=yearly_data,
                           time_of_day_data=time_of_day_data,
                           monthly_data=monthly_data,
                           years=years,
                           current_year=current_year)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    setup_app()
    app.run(debug=True)
