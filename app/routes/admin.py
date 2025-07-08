from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_superuser,
    require_permission,
    require_role,
    require_superadmin,
    require_superadmin_or_admin,
)
from app.database.base import get_db
from app.models.schemas import Permission as PermissionSchema
from app.models.schemas import (
    PermissionCreate,
    PermissionUpdate,
)
from app.models.schemas import Role as RoleSchema
from app.models.schemas import (
    RoleCreate,
    RoleUpdate,
)
from app.models.schemas import User as UserSchema
from app.models.user import Permission, Role, User

router = APIRouter(tags=["admin"])


# User management endpoints
@router.get("/users", response_model=List[UserSchema])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
):
    """List all users (requires users:read permission)"""
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:read")),
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
    current_user: User = Depends(require_superadmin_or_admin()),
):
    """Assign role to user (requires superadmin or admin privileges)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Proteção especial: apenas superadmin pode atribuir role superadmin
    if role.name == "superadmin" and not (
        current_user.is_superuser or current_user.has_role("superadmin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can assign superadmin role",
        )

    # Proteção: admin não pode alterar roles de superadmin
    if user.has_role("superadmin") and not (
        current_user.is_superuser or current_user.has_role("superadmin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superadmin user roles",
        )

    if role not in user.roles:
        user.roles.append(role)
        db.commit()

    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin_or_admin()),
):
    """Remove role from user (requires superadmin or admin privileges)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Proteção especial: apenas superadmin pode remover role superadmin
    if role.name == "superadmin" and not (
        current_user.is_superuser or current_user.has_role("superadmin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can remove superadmin role",
        )

    # Proteção: admin não pode alterar roles de superadmin
    if user.has_role("superadmin") and not (
        current_user.is_superuser or current_user.has_role("superadmin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superadmin user roles",
        )

    if role in user.roles:
        user.roles.remove(role)
        db.commit()

    return {"message": f"Role '{role.name}' removed from user '{user.username}'"}


# Role management endpoints
@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:read")),
):
    """List all roles (requires roles:read permission)"""
    return db.query(Role).all()


@router.post("/roles", response_model=RoleSchema)
async def create_role(
    role_create: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles:create")),
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
    current_user: User = Depends(require_permission("roles:update")),
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
    current_user: User = Depends(require_superadmin()),
):
    """Delete role (requires superadmin privileges)"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Proteção: não pode deletar role superadmin
    if role.name == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete superadmin role",
        )

    # Proteção: não pode deletar roles críticos
    critical_roles = ["admin", "superadmin"]
    if role.name in critical_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete critical role '{role.name}'",
        )

    db.delete(role)
    db.commit()
    return {"message": f"Role '{role.name}' deleted"}


# Permission management endpoints
@router.get("/permissions", response_model=List[PermissionSchema])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("permissions:read")),
):
    """List all permissions (requires permissions:read permission)"""
    return db.query(Permission).all()


@router.post("/permissions", response_model=PermissionSchema)
async def create_permission(
    permission_create: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("permissions:create")),
):
    """Create new permission (requires permissions:create permission)"""
    # Check if permission already exists
    existing_permission = (
        db.query(Permission).filter(Permission.name == permission_create.name).first()
    )
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
    current_user: User = Depends(require_permission("roles:update")),
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
    current_user: User = Depends(require_permission("roles:update")),
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

    return {
        "message": f"Permission '{permission.name}' removed from role '{role.name}'"
    }


# Superadmin management endpoints
@router.post("/users/{user_id}/superadmin")
async def promote_to_superadmin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin()),
):
    """Promote user to superadmin (requires superadmin privileges)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificar se já é superuser
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="User is already a superuser")

    # Verificar se já tem role superadmin
    if user.has_role("superadmin"):
        raise HTTPException(status_code=400, detail="User already has superadmin role")

    # Adicionar role superadmin
    superadmin_role = db.query(Role).filter(Role.name == "superadmin").first()
    if not superadmin_role:
        raise HTTPException(status_code=500, detail="Superadmin role not found")

    user.roles.append(superadmin_role)
    user.is_superuser = True  # Também marcar como superuser
    db.commit()

    return {"message": f"User '{user.username}' promoted to superadmin"}


@router.delete("/users/{user_id}/superadmin")
async def revoke_superadmin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin()),
):
    """Revoke superadmin privileges (requires superadmin privileges)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Não pode remover de si mesmo se for o último superadmin
    if user.id == current_user.id:
        superadmin_count = (
            db.query(User)
            .filter(
                (User.is_superuser == True)
                | (
                    User.id.in_(
                        db.query(User.id)
                        .join(User.roles)
                        .filter(Role.name == "superadmin")
                    )
                )
            )
            .count()
        )

        if superadmin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke superadmin from yourself - you are the last superadmin",
            )

    # Remover role superadmin
    superadmin_role = db.query(Role).filter(Role.name == "superadmin").first()
    if superadmin_role and superadmin_role in user.roles:
        user.roles.remove(superadmin_role)

    user.is_superuser = False  # Também remover flag superuser
    db.commit()

    return {"message": f"Superadmin privileges revoked from user '{user.username}'"}
