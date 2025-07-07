from sqlalchemy.orm import Session
from app.database.base import SessionLocal, create_tables
from app.models.user import User, Role, Permission
from app.auth.utils import get_password_hash


def init_permissions(db: Session):
    """Create default permissions"""
    permissions = [
        # User permissions
        {"name": "users:create", "description": "Create users", "resource": "users", "action": "create"},
        {"name": "users:read", "description": "Read users", "resource": "users", "action": "read"},
        {"name": "users:update", "description": "Update users", "resource": "users", "action": "update"},
        {"name": "users:delete", "description": "Delete users", "resource": "users", "action": "delete"},
        
        # Role permissions
        {"name": "roles:create", "description": "Create roles", "resource": "roles", "action": "create"},
        {"name": "roles:read", "description": "Read roles", "resource": "roles", "action": "read"},
        {"name": "roles:update", "description": "Update roles", "resource": "roles", "action": "update"},
        {"name": "roles:delete", "description": "Delete roles", "resource": "roles", "action": "delete"},
        
        # Permission permissions
        {"name": "permissions:create", "description": "Create permissions", "resource": "permissions", "action": "create"},
        {"name": "permissions:read", "description": "Read permissions", "resource": "permissions", "action": "read"},
        {"name": "permissions:update", "description": "Update permissions", "resource": "permissions", "action": "update"},
        {"name": "permissions:delete", "description": "Delete permissions", "resource": "permissions", "action": "delete"},
        
        # Posts permissions
        {"name": "posts:create", "description": "Create posts", "resource": "posts", "action": "create"},
        {"name": "posts:read", "description": "Read posts", "resource": "posts", "action": "read"},
        {"name": "posts:update", "description": "Update posts", "resource": "posts", "action": "update"},
        {"name": "posts:delete", "description": "Delete posts", "resource": "posts", "action": "delete"},
        
        # Settings permissions
        {"name": "settings:read", "description": "Read settings", "resource": "settings", "action": "read"},
        {"name": "settings:update", "description": "Update settings", "resource": "settings", "action": "update"},
    ]
    
    for perm_data in permissions:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            permission = Permission(**perm_data)
            db.add(permission)
    
    db.commit()


def init_roles(db: Session):
    """Create default roles"""
    roles_data = [
        {
            "name": "admin",
            "description": "Administrator with full access",
            "permissions": [
                "users:create", "users:read", "users:update", "users:delete",
                "roles:create", "roles:read", "roles:update", "roles:delete",
                "permissions:create", "permissions:read", "permissions:update", "permissions:delete",
                "posts:create", "posts:read", "posts:update", "posts:delete",
                "settings:read", "settings:update"
            ]
        },
        {
            "name": "manager",
            "description": "Manager with limited admin access",
            "permissions": [
                "users:read", "users:update",
                "roles:read",
                "permissions:read",
                "posts:create", "posts:read", "posts:update", "posts:delete",
                "settings:read"
            ]
        },
        {
            "name": "editor",
            "description": "Content editor",
            "permissions": [
                "posts:create", "posts:read", "posts:update"
            ]
        },
        {
            "name": "viewer",
            "description": "View-only access",
            "permissions": [
                "posts:read"
            ]
        }
    ]
    
    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(
                name=role_data["name"],
                description=role_data["description"]
            )
            db.add(role)
            db.commit()
            db.refresh(role)
            
            # Add permissions to role
            for perm_name in role_data["permissions"]:
                permission = db.query(Permission).filter(Permission.name == perm_name).first()
                if permission:
                    role.permissions.append(permission)
            
            db.commit()


def init_admin_user(db: Session):
    """Create default admin user"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_password = get_password_hash("admin123")
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="System Administrator",
            hashed_password=hashed_password,
            is_superuser=True,
            provider="basic"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Assign admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            admin_user.roles.append(admin_role)
            db.commit()


def initialize_database():
    """Initialize database with default data"""
    create_tables()
    
    db = SessionLocal()
    try:
        print("Initializing permissions...")
        init_permissions(db)
        
        print("Initializing roles...")
        init_roles(db)
        
        print("Initializing admin user...")
        init_admin_user(db)
        
        print("Database initialization completed!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database() 