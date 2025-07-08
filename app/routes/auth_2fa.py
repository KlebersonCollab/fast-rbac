"""
Rotas de Autenticação 2FA (TOTP)
Endpoints para configurar e gerenciar autenticação de 2 fatores
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.schemas import (
    TotpSetupRequest, TotpSetupResponse, TotpVerifyRequest, TotpVerifyResponse,
    TotpEnableRequest, TotpDisableRequest, TotpStatusResponse,
    LoginWith2FARequest, Token
)
from app.services.totp_service import totp_service
from app.auth.utils import create_access_token
from app.services.cache_service import cache_service
from typing import Dict, Any


router = APIRouter()


@router.get("/status", response_model=TotpStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna status do 2FA para o usuário atual
    """
    return totp_service.get_totp_status(current_user)


@router.post("/setup", response_model=TotpSetupResponse)
async def setup_2fa(
    request: TotpSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configura 2FA para o usuário atual
    Retorna secret, QR code e códigos de backup
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA já está habilitado. Desabilite primeiro para reconfigurar."
        )
    
    try:
        result = totp_service.setup_totp(current_user, db)
        
        # Invalidar cache do usuário
        if cache_service.is_available():
            await cache_service.invalidate_user_cache(current_user.id)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao configurar 2FA: {str(e)}"
        )


@router.post("/enable", response_model=TotpVerifyResponse)
async def enable_2fa(
    request: TotpEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Habilita 2FA após verificação do código TOTP
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA já está habilitado"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure o 2FA primeiro usando /setup"
        )
    
    result = totp_service.enable_2fa(current_user, request.totp_code, db)
    
    if result.success:
        # Invalidar cache do usuário
        if cache_service.is_available():
            await cache_service.invalidate_user_cache(current_user.id)
    
    return result


@router.post("/disable", response_model=TotpVerifyResponse)
async def disable_2fa(
    request: TotpDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Desabilita 2FA após verificação de senha e código
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA não está habilitado"
        )
    
    result = totp_service.disable_2fa(
        current_user, 
        request.password, 
        request.totp_code, 
        request.backup_code, 
        db
    )
    
    if result.success:
        # Invalidar cache do usuário
        if cache_service.is_available():
            await cache_service.invalidate_user_cache(current_user.id)
    
    return result


@router.post("/verify", response_model=TotpVerifyResponse)
async def verify_2fa_code(
    request: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica código TOTP (para testes)
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA não está habilitado"
        )
    
    return totp_service.verify_totp(current_user, request.totp_code)


@router.post("/regenerate-backup-codes", response_model=TotpVerifyResponse)
async def regenerate_backup_codes(
    request: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenera códigos de backup após verificação TOTP
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA não está habilitado"
        )
    
    result = totp_service.regenerate_backup_codes(current_user, request.totp_code, db)
    
    if result.success:
        # Invalidar cache do usuário
        if cache_service.is_available():
            await cache_service.invalidate_user_cache(current_user.id)
    
    return result


@router.post("/login", response_model=Token)
async def login_with_2fa(
    request: LoginWith2FARequest,
    db: Session = Depends(get_db)
):
    """
    Login com suporte a 2FA
    """
    success, message, user = totp_service.authenticate_with_2fa(
        request.username,
        request.password,
        request.totp_code,
        request.backup_code,
        db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token de acesso
    access_token = create_access_token(data={"sub": user.username})
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/backup-codes/count")
async def get_backup_codes_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna número de códigos de backup restantes
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA não está habilitado"
        )
    
    import json
    count = 0
    if current_user.backup_codes:
        try:
            codes = json.loads(current_user.backup_codes)
            count = len(codes)
        except:
            count = 0
    
    return {"backup_codes_count": count}


@router.get("/qr-code")
async def get_qr_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna QR code para configuração manual
    (apenas se 2FA ainda não estiver habilitado)
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA já está habilitado"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure o 2FA primeiro usando /setup"
        )
    
    try:
        import pyotp
        import segno
        from io import BytesIO
        from base64 import b64encode
        
        # Descriptografar secret
        secret = totp_service._decrypt_secret(current_user.totp_secret)
        
        # Criar provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name=totp_service.issuer
        )
        
        # Gerar QR code
        qr_code = segno.make_qr(provisioning_uri)
        buffer = BytesIO()
        qr_code.save(buffer, kind='svg', scale=5)
        qr_code_svg = buffer.getvalue().decode('utf-8')
        
        # Retornar como data URL
        qr_code_url = f"data:image/svg+xml;base64,{b64encode(qr_code_svg.encode()).decode()}"
        
        return {
            "qr_code_url": qr_code_url,
            "manual_entry_key": secret,
            "issuer": totp_service.issuer,
            "account": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar QR code: {str(e)}"
        )


@router.post("/test-backup-code", response_model=TotpVerifyResponse)
async def test_backup_code(
    request: TotpVerifyRequest,  # Reutiliza schema, mas usa como backup_code
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Testa um código de backup (sem removê-lo)
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA não está habilitado"
        )
    
    if not current_user.backup_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum código de backup disponível"
        )
    
    try:
        import json
        
        # Carregar códigos de backup
        hashed_codes = json.loads(current_user.backup_codes)
        
        # Verificar se o código é válido (sem removê-lo)
        is_valid = totp_service.verify_backup_code(request.totp_code, hashed_codes)
        
        if is_valid:
            return TotpVerifyResponse(
                success=True,
                message="Código de backup válido"
            )
        else:
            return TotpVerifyResponse(
                success=False,
                message="Código de backup inválido"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar código de backup: {str(e)}"
        ) 