"""
TOTP (Time-based One-Time Password) Service
Implementa autenticação de 2 fatores usando TOTP (RFC 6238)
"""

import hashlib
import json
import secrets
from base64 import b64encode
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode
import segno
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.schemas import TotpSetupResponse, TotpStatusResponse, TotpVerifyResponse
from app.models.user import User


class TotpService:
    """Serviço de autenticação TOTP (2FA)"""

    def __init__(self):
        self.issuer = settings.app_name
        self.key = settings.secret_key.encode()[:32]  # 32 bytes for Fernet
        self.cipher = Fernet(b64encode(self.key))

    def _encrypt_secret(self, secret: str) -> str:
        """Criptografa o secret TOTP"""
        return self.cipher.encrypt(secret.encode()).decode()

    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Descriptografa o secret TOTP"""
        return self.cipher.decrypt(encrypted_secret.encode()).decode()

    def generate_secret(self) -> str:
        """Gera um novo secret TOTP"""
        return pyotp.random_base32()

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Gera códigos de backup únicos"""
        codes = []
        for _ in range(count):
            # Gera código de 8 dígitos
            code = f"{secrets.randbelow(100000000):08d}"
            codes.append(code)
        return codes

    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Criptografa códigos de backup para armazenamento"""
        hashed_codes = []
        for code in codes:
            # Usar hash SHA-256 para códigos de backup
            hashed = hashlib.sha256(f"{code}{self.key}".encode()).hexdigest()
            hashed_codes.append(hashed)
        return hashed_codes

    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> bool:
        """Verifica se um código de backup é válido"""
        code_hash = hashlib.sha256(f"{code}{self.key}".encode()).hexdigest()
        return code_hash in hashed_codes

    def setup_totp(self, user: User, db: Session) -> TotpSetupResponse:
        """
        Configura TOTP para um usuário
        Retorna secret, QR code e códigos de backup
        """
        # Gerar novo secret
        secret = self.generate_secret()

        # Criar provisioning URI para QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email, issuer_name=self.issuer
        )

        # Gerar QR code como SVG
        qr_code = segno.make_qr(provisioning_uri)
        buffer = BytesIO()
        qr_code.save(buffer, kind="svg", scale=5)
        qr_code_svg = buffer.getvalue().decode("utf-8")

        # Gerar QR code como data URL
        qr_code_url = (
            f"data:image/svg+xml;base64,{b64encode(qr_code_svg.encode()).decode()}"
        )

        # Gerar códigos de backup
        backup_codes = self.generate_backup_codes()
        hashed_backup_codes = self.hash_backup_codes(backup_codes)

        # Salvar secret criptografado (mas não habilitar ainda)
        encrypted_secret = self._encrypt_secret(secret)
        user.totp_secret = encrypted_secret
        user.backup_codes = json.dumps(hashed_backup_codes)
        user.is_2fa_enabled = False  # Só habilita após verificação

        db.commit()

        return TotpSetupResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            manual_entry_key=secret,
            backup_codes=backup_codes,
        )

    def verify_totp(
        self, user: User, totp_code: str, window: int = 1
    ) -> TotpVerifyResponse:
        """
        Verifica código TOTP
        window: permite códigos de períodos anteriores/posteriores
        """
        if not user.totp_secret:
            return TotpVerifyResponse(
                success=False, message="2FA não está configurado para este usuário"
            )

        try:
            # Descriptografar secret
            secret = self._decrypt_secret(user.totp_secret)
            totp = pyotp.TOTP(secret)

            # Verificar código atual
            current_time = datetime.now()

            # Verificar se o código já foi usado (prevenir replay)
            if user.last_totp_used == totp_code:
                return TotpVerifyResponse(
                    success=False, message="Código TOTP já foi usado"
                )

            # Verificar código com janela de tempo
            is_valid = totp.verify(totp_code, valid_window=window)

            if is_valid:
                return TotpVerifyResponse(success=True, message="Código TOTP válido")
            else:
                return TotpVerifyResponse(success=False, message="Código TOTP inválido")

        except Exception as e:
            return TotpVerifyResponse(
                success=False, message=f"Erro na verificação TOTP: {str(e)}"
            )

    def verify_backup_code(
        self, user: User, backup_code: str, db: Session
    ) -> TotpVerifyResponse:
        """
        Verifica código de backup e o remove da lista
        """
        if not user.backup_codes:
            return TotpVerifyResponse(
                success=False, message="Nenhum código de backup disponível"
            )

        try:
            # Carregar códigos de backup
            hashed_codes = json.loads(user.backup_codes)

            # Verificar se o código é válido
            if not self.verify_backup_code(backup_code, hashed_codes):
                return TotpVerifyResponse(
                    success=False, message="Código de backup inválido"
                )

            # Remover código usado
            code_hash = hashlib.sha256(f"{backup_code}{self.key}".encode()).hexdigest()
            hashed_codes.remove(code_hash)

            # Atualizar banco de dados
            user.backup_codes = json.dumps(hashed_codes)
            db.commit()

            return TotpVerifyResponse(
                success=True,
                message="Código de backup válido",
                backup_codes=None,  # Não retorna códigos restantes por segurança
            )

        except Exception as e:
            return TotpVerifyResponse(
                success=False,
                message=f"Erro na verificação do código de backup: {str(e)}",
            )

    def enable_2fa(self, user: User, totp_code: str, db: Session) -> TotpVerifyResponse:
        """
        Habilita 2FA após verificação do código TOTP
        """
        if user.is_2fa_enabled:
            return TotpVerifyResponse(success=False, message="2FA já está habilitado")

        # Verificar código TOTP
        verify_result = self.verify_totp(user, totp_code)

        if verify_result.success:
            # Habilitar 2FA
            user.is_2fa_enabled = True
            user.last_totp_used = totp_code
            db.commit()

            return TotpVerifyResponse(
                success=True, message="2FA habilitado com sucesso"
            )
        else:
            return verify_result

    def disable_2fa(
        self,
        user: User,
        password: str,
        totp_code: str = None,
        backup_code: str = None,
        db: Session = None,
    ) -> TotpVerifyResponse:
        """
        Desabilita 2FA após verificação de senha e código
        """
        from app.auth.password import verify_password

        if not user.is_2fa_enabled:
            return TotpVerifyResponse(success=False, message="2FA não está habilitado")

        # Verificar senha
        if not verify_password(password, user.hashed_password):
            return TotpVerifyResponse(success=False, message="Senha incorreta")

        # Verificar código TOTP ou backup code
        if totp_code:
            verify_result = self.verify_totp(user, totp_code)
            if not verify_result.success:
                return verify_result
        elif backup_code:
            verify_result = self.verify_backup_code(user, backup_code, db)
            if not verify_result.success:
                return verify_result
        else:
            return TotpVerifyResponse(
                success=False, message="Código TOTP ou de backup é necessário"
            )

        # Desabilitar 2FA
        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        user.last_totp_used = None
        db.commit()

        return TotpVerifyResponse(success=True, message="2FA desabilitado com sucesso")

    def regenerate_backup_codes(
        self, user: User, totp_code: str, db: Session
    ) -> TotpVerifyResponse:
        """
        Regenera códigos de backup após verificação TOTP
        """
        if not user.is_2fa_enabled:
            return TotpVerifyResponse(success=False, message="2FA não está habilitado")

        # Verificar código TOTP
        verify_result = self.verify_totp(user, totp_code)

        if verify_result.success:
            # Gerar novos códigos de backup
            new_backup_codes = self.generate_backup_codes()
            hashed_codes = self.hash_backup_codes(new_backup_codes)

            # Atualizar banco de dados
            user.backup_codes = json.dumps(hashed_codes)
            db.commit()

            return TotpVerifyResponse(
                success=True,
                message="Códigos de backup regenerados com sucesso",
                backup_codes=new_backup_codes,
            )
        else:
            return verify_result

    def get_totp_status(self, user: User) -> TotpStatusResponse:
        """
        Retorna status do 2FA para o usuário
        """
        has_backup_codes = False
        if user.backup_codes:
            try:
                codes = json.loads(user.backup_codes)
                has_backup_codes = len(codes) > 0
            except:
                has_backup_codes = False

        return TotpStatusResponse(
            is_2fa_enabled=user.is_2fa_enabled,
            has_backup_codes=has_backup_codes,
            setup_date=user.updated_at if user.is_2fa_enabled else None,
        )

    def authenticate_with_2fa(
        self,
        username: str,
        password: str,
        totp_code: str = None,
        backup_code: str = None,
        db: Session = None,
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Autentica usuário com 2FA
        Retorna: (success, message, user)
        """
        from app.auth.password import verify_password

        # Verificar usuário e senha
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return False, "Credenciais inválidas", None

        # Se 2FA não estiver habilitado, permitir login
        if not user.is_2fa_enabled:
            return True, "Login realizado com sucesso", user

        # 2FA está habilitado, verificar código
        if totp_code:
            verify_result = self.verify_totp(user, totp_code)
            if verify_result.success:
                # Atualizar último código usado
                user.last_totp_used = totp_code
                db.commit()
                return True, "Login com 2FA realizado com sucesso", user
            else:
                return False, verify_result.message, None

        elif backup_code:
            verify_result = self.verify_backup_code(user, backup_code, db)
            if verify_result.success:
                return True, "Login com código de backup realizado com sucesso", user
            else:
                return False, verify_result.message, None
        else:
            return False, "Código 2FA é necessário", None


# Instância global do serviço
totp_service = TotpService()
