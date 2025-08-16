from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    is_admin = db.Column(db.Boolean, default=False)

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    pin_code = db.Column(db.String(10))
    maximum_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='A')  # A - Available, O - Occupied
    
    reservations = db.relationship('Reservation', backref='spot', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(1), default='A')  # 'A' for Active, 'I' for Inactive
    user = db.relationship('User', backref='reservations')
    #spot = db.relationship('ParkingSpot', backref='reservations')

'''
    def total_cost(self):
        if self.leaving_timestamp:
            duration = self.leaving_timestamp - self.parking_timestamp
            hours = max(duration.total_seconds() / 3600, 1)
            return round(hours * self.cost_per_hour, 2)
        return 0
 '''   
    

