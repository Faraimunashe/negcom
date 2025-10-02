from datetime import datetime, timedelta
from app import db
from app.models import Notification

class NotificationService:
    @staticmethod
    def create_notification(user_id, title, message, type='info', category='system', 
                          action_url=None, related_id=None, related_type=None):
        """Create a new notification and return it"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=type,
                category=category,
                action_url=action_url,
                related_id=related_id,
                related_type=related_type
            )
            db.session.add(notification)
            db.session.commit()
            return notification
        except Exception as e:
            db.session.rollback()
            print(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications for user"""
        try:
            return Notification.query.filter_by(user_id=user_id, is_read=False).count()
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0
    
    @staticmethod
    def get_recent_notifications(user_id, limit=10):
        """Get recent notifications for user"""
        try:
            return Notification.query.filter_by(user_id=user_id)\
                .order_by(Notification.created_at.desc())\
                .limit(limit).all()
        except Exception as e:
            print(f"Error getting recent notifications: {e}")
            return []
    
    @staticmethod
    def get_new_notifications_since(user_id, since_date):
        """Get new notifications since a specific date"""
        try:
            return Notification.query.filter(
                Notification.user_id == user_id,
                Notification.created_at > since_date
            ).order_by(Notification.created_at.desc()).all()
        except Exception as e:
            print(f"Error getting new notifications: {e}")
            return []
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark specific notification as read"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id, 
                user_id=user_id
            ).first()
            if notification:
                notification.is_read = True
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Error marking notification as read: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for user"""
        try:
            Notification.query.filter_by(user_id=user_id, is_read=False)\
                .update({'is_read': True})
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error marking all notifications as read: {e}")
            return False
    
    @staticmethod
    def delete_notification(notification_id, user_id):
        """Delete a notification"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id, 
                user_id=user_id
            ).first()
            if notification:
                db.session.delete(notification)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting notification: {e}")
            return False
    
    @staticmethod
    def cleanup_old_notifications(days=30):
        """Clean up notifications older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            old_notifications = Notification.query.filter(
                Notification.created_at < cutoff_date
            ).all()
            
            for notification in old_notifications:
                db.session.delete(notification)
            
            db.session.commit()
            return len(old_notifications)
        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning up old notifications: {e}")
            return 0
