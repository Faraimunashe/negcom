from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.notification_service import NotificationService

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/api/notifications')
@login_required
def get_notifications():
    """Get user notifications"""
    try:
        notifications = NotificationService.get_recent_notifications(current_user.id)
        unread_count = NotificationService.get_unread_count(current_user.id)
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'category': n.category,
                'is_read': n.is_read,
                'action_url': n.action_url,
                'created_at': n.created_at.isoformat()
            } for n in notifications],
            'unread_count': unread_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/check')
@login_required
def check_new_notifications():
    """Check for new notifications since timestamp"""
    try:
        since = request.args.get('since', 0)
        since_date = datetime.fromtimestamp(int(since) / 1000)
        
        new_notifications = NotificationService.get_new_notifications_since(
            current_user.id, since_date
        )
        
        return jsonify({
            'new_notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'action_url': n.action_url,
                'created_at': n.created_at.isoformat()
            } for n in new_notifications]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        success = NotificationService.mark_as_read(notification_id, current_user.id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    try:
        success = NotificationService.mark_all_as_read(current_user.id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        success = NotificationService.delete_notification(notification_id, current_user.id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/notifications')
@login_required
def notifications_page():
    """Full notifications page"""
    from flask import render_template
    
    notifications = NotificationService.get_recent_notifications(current_user.id, limit=50)
    unread_count = NotificationService.get_unread_count(current_user.id)
    
    return render_template('notifications/index.html', 
                         notifications=notifications, 
                         unread_count=unread_count)
