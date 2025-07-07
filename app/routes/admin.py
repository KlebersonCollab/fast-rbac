from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.base import get_db
from app.auth.dependencies import get_current_superuser, require_permission, require_role
from app.models.user import User, Role, Permission
from app.models.schemas import (
    User as UserSchema, Role as RoleSchema, Permission as PermissionSchema,
    RoleCreate, RoleUpdate, PermissionCreate, PermissionUpdate
)

router = APIRouter(prefix="/admin", tags=["admin"])


# User management endpoints
@router.get("/users", response_model=List[UserSchema])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read"))
):
    """List all users (requires users:read permission)"""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read"))
):
    """Get user by ID (requires users:read permission)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/roles/{role_id}")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:update"))
):
    """Assign role to user (requires users:update permission)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role not in user.roles:
        user.roles.append(role)
        db.commit()
    
    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:update"))
):
    """Remove role from user (requires users:update permission)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role in user.roles:
        user.roles.remove(role)
        db.commit()
    
    return {"message": f"Role '{role.name}' removed from user '{user.username}'"}


# Role management endpoints
@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:read"))
):
    """List all roles (requires roles:read permission)"""
    return db.query(Role).all()


@router.post("/roles", response_model=RoleSchema)
async def create_role(
    role_create: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:create"))
):
    """Create new role (requires roles:create permission)"""
    # Check if role already exists
    existing_role = db.query(Role).filter(Role.name == role_create.name).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    db_role = Role(**role_create.dict())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


@router.put("/roles/{role_id}", response_model=RoleSchema)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update"))
):
    """Update role (requires roles:update permission)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_data = role_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:delete"))
):
    """Delete role (requires roles:delete permission)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    db.delete(role)
    db.commit()
    return {"message": f"Role '{role.name}' deleted"}


# Permission management endpoints
@router.get("/permissions", response_model=List[PermissionSchema])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("permissions:read"))
):
    """List all permissions (requires permissions:read permission)"""
    return db.query(Permission).all()


@router.post("/permissions", response_model=PermissionSchema)
async def create_permission(
    permission_create: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("permissions:create"))
):
    """Create new permission (requires permissions:create permission)"""
    # Check if permission already exists
    existing_permission = db.query(Permission).filter(
        Permission.name == permission_create.name
    ).first()
    if existing_permission:
        raise HTTPException(status_code=400, detail="Permission already exists")
    
    db_permission = Permission(**permission_create.dict())
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission


@router.post("/roles/{role_id}/permissions/{permission_id}")
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update"))
):
    """Assign permission to role (requires roles:update permission)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()
    
    return {"message": f"Permission '{permission.name}' assigned to role '{role.name}'"}


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:update"))
):
    """Remove permission from role (requires roles:update permission)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()
    
    return {"message": f"Permission '{permission.name}' removed from role '{role.name}'"} 