import requests
import json
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class DiditAPI:
    """Clase para manejar la integración con la API de DIDIT"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'DIDIT_API_KEY', None)
        self.base_url = getattr(settings, 'DIDIT_BASE_URL', 'https://verification.didit.me')
        self.workflow_id = getattr(settings, 'DIDIT_WORKFLOW_ID', None)
        self.webhook_secret = getattr(settings, 'DIDIT_WEBHOOK_SECRET_KEY', None)
        
        if not self.api_key:
            raise ValueError("DIDIT_API_KEY no está configurado en las variables de entorno")
        if not self.workflow_id:
            raise ValueError("DIDIT_WORKFLOW_ID no está configurado en las variables de entorno")
    
    def test_authentication(self):
        """
        Función para probar diferentes métodos de autenticación con DIDIT
        """
        test_url = f"{self.base_url}/v2/session/"  # Endpoint real de DIDIT
        
        # Diferentes formatos de autorización a probar
        auth_formats = [
            {'X-Api-Key': self.api_key},  # Formato oficial según documentación
            {'X-API-KEY': self.api_key},
            {'Authorization': f'Bearer {self.api_key}'},
            {'Authorization': f'API-KEY {self.api_key}'},
            {'Authorization': f'Token {self.api_key}'},
            {'apikey': self.api_key},
            {'api-key': self.api_key}
        ]
        
        results = []
        
        for i, headers in enumerate(auth_formats):
            headers['Content-Type'] = 'application/json'
            try:
                response = requests.get(test_url, headers=headers, timeout=10)
                results.append({
                    'format': f"Formato {i+1}",
                    'headers': headers,
                    'status_code': response.status_code,
                    'success': response.status_code != 401,
                    'response': response.text[:200]  # Solo los primeros 200 caracteres
                })
            except Exception as e:
                results.append({
                    'format': f"Formato {i+1}",
                    'headers': headers,
                    'status_code': 'Error',
                    'success': False,
                    'response': str(e)
                })
        
        return results

    def create_verification_session(self, user_data):
        """
        Crear una sesión de verificación en DIDIT siguiendo la documentación oficial
        
        Args:
            user_data (dict): Datos del usuario para la verificación
            
        Returns:
            dict: Respuesta de la API de DIDIT
        """
        url = f"{self.base_url}/v2/session/"
        
        # Headers según documentación oficial de DIDIT
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }
        
        # Preparar los datos según la estructura oficial de DIDIT
        payload = {
            'workflow_id': self.workflow_id,
            'callback': user_data.get('redirect_url'),
            'vendor_data': f"user-{user_data.get('user_id')}",
            'metadata': {
                'user_id': str(user_data.get('user_id')),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'country': user_data.get('country', 'PE'),
                'registration_date': timezone.now().isoformat()
            },
            'contact_details': {
                'email': user_data.get('email'),
                'email_lang': user_data.get('language', 'es')
            }
        }
        
        # Agregar teléfono si está disponible
        if user_data.get('phone'):
            payload['contact_details']['phone'] = user_data.get('phone')
        
        try:
            logger.info(f"Creando sesión DIDIT para usuario {user_data.get('user_id')} con workflow {self.workflow_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # Registrar detalles de la respuesta para debugging
            logger.info(f"Respuesta DIDIT - Status: {response.status_code}, Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Sesión DIDIT creada exitosamente para usuario {user_data.get('user_id')}")
                return {
                    'success': True,
                    'session_id': result.get('session_id'),
                    'session_url': result.get('url'),  # Según la documentación, el campo se llama 'url'
                    'session_token': result.get('session_token'),
                    'session_number': result.get('session_number'),
                    'vendor_data': result.get('vendor_data'),
                    'metadata': result.get('metadata'),
                    'workflow_id': result.get('workflow_id'),
                    'callback': result.get('callback'),
                    'status': result.get('status'),
                    'data': result
                }
            else:
                # Error HTTP
                error_detail = response.text if response.text else f"HTTP {response.status_code}"
                logger.error(f"Error HTTP al crear sesión DIDIT: {response.status_code} - {error_detail}")
                return {
                    'success': False,
                    'error': f"Error HTTP {response.status_code}: {error_detail}",
                    'data': None
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al crear sesión DIDIT: {str(e)}")
            return {
                'success': False,
                'error': f"Error de conexión: {str(e)}",
                'data': None
            }
        except Exception as e:
            logger.error(f"Error inesperado al crear sesión DIDIT: {str(e)}")
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'data': None
            }
    
    def get_verification_status(self, session_id):
        """
        Obtener el estado de una sesión de verificación usando el endpoint /v2/session/{sessionId}/decision/
        
        Args:
            session_id (str): ID de la sesión de verificación
            
        Returns:
            dict: Estado de la verificación con datos procesados
        """
        url = f"{self.base_url}/v2/session/{session_id}/decision/"
        
        headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info(f"Consultando estado de sesión DIDIT {session_id}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Procesar la respuesta según la estructura de DIDIT
                processed_result = self._process_decision_response(result)
                logger.info(f"Estado obtenido para sesión {session_id}: {processed_result.get('status', 'unknown')}")
                
                return {
                    'success': True,
                    'data': processed_result
                }
            elif response.status_code == 404:
                logger.warning(f"Sesión DIDIT {session_id} no encontrada")
                return {
                    'success': False,
                    'error': 'Sesión no encontrada',
                    'data': None
                }
            elif response.status_code == 204:
                # Estado 204 significa que la sesión no tiene decisión aún (pendiente)
                logger.info(f"Sesión DIDIT {session_id} aún pendiente (204 No Content)")
                return {
                    'success': True,
                    'data': {
                        'status': 'pending',
                        'session_id': session_id,
                        'message': 'Verificación en proceso'
                    }
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Error al obtener estado de sesión DIDIT {session_id}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'data': None
                }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al obtener estado de sesión DIDIT {session_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Error de conexión: {str(e)}",
                'data': None
            }
        except Exception as e:
            logger.error(f"Error inesperado al obtener estado de sesión DIDIT {session_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'data': None
            }
    
    def _process_decision_response(self, response_data):
        """
        Procesar la respuesta del endpoint /decision/ de DIDIT
        
        Args:
            response_data (dict): Respuesta cruda de la API
            
        Returns:
            dict: Datos procesados y estructurados
        """
        try:
            # Log detallado de lo que devuelve DIDIT para debugging
            logger.info(f"Procesando respuesta DIDIT: {response_data}")
            
            # Extraer información básica
            session_id = response_data.get('session_id')
            status = response_data.get('status', 'unknown')
            
            # Log del estado raw
            logger.info(f"Estado raw de DIDIT: '{status}' (tipo: {type(status)})")
            
            # Obtener resultado de verificación
            verification_result = response_data.get('verification_result', {})
            overall_result = verification_result.get('overall_result', 'unknown')
            
            # Log del resultado overall
            logger.info(f"Overall result de DIDIT: '{overall_result}' (tipo: {type(overall_result)})")
            
            # Mapear estados según documentación de DIDIT
            # DIDIT puede devolver diferentes estados, incluyendo "Approved"
            status_mapping = {
                'completed': 'completed',
                'approved': 'completed',  # DIDIT devuelve "Approved" cuando está aprobado
                'Approved': 'completed',  # Capitalizado también
                'failed': 'failed',
                'rejected': 'failed',
                'Rejected': 'failed',
                'pending': 'pending',
                'processing': 'processing', 
                'submitted': 'submitted',
                'expired': 'expired',
                'cancelled': 'cancelled'
            }
            
            mapped_status = status_mapping.get(status, status)
            logger.info(f"Estado mapeado: '{mapped_status}'")
            
            # Determinar si está verificado exitosamente
            # Si el estado es "Approved" o "completed", considerarlo como verificado
            is_verified = (
                mapped_status == 'completed' or 
                status.lower() == 'approved' or
                (mapped_status == 'completed' and overall_result in ['pass', 'approved', 'Approved', ''])
            )
            
            logger.info(f"¿Está verificado? {is_verified}")
            
            result = {
                'session_id': session_id,
                'status': mapped_status,
                'overall_result': overall_result,
                'is_verified': is_verified,
                'verification_result': verification_result,
                'timestamp': response_data.get('created_at') or response_data.get('updated_at'),
                'workflow_id': response_data.get('workflow_id'),
                'vendor_data': response_data.get('vendor_data'),
                'raw_data': response_data
            }
            
            logger.info(f"Resultado final procesado: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error al procesar respuesta de decisión DIDIT: {str(e)}")
            return {
                'session_id': response_data.get('session_id', 'unknown'),
                'status': 'error',
                'error': str(e),
                'raw_data': response_data
            }
    
    def process_webhook_data(self, webhook_data):
        """
        Procesar datos del webhook de DIDIT
        
        Args:
            webhook_data (dict): Datos recibidos del webhook
            
        Returns:
            dict: Datos procesados
        """
        try:
            session_id = webhook_data.get('session_id')
            status = webhook_data.get('status')
            verification_result = webhook_data.get('verification_result', {})
            
            # Mapear estados de DIDIT a nuestros estados internos
            status_mapping = {
                'completed': 'completed',
                'failed': 'failed',
                'pending': 'pending',
                'expired': 'expired',
                'cancelled': 'cancelled'
            }
            
            mapped_status = status_mapping.get(status, 'unknown')
            
            return {
                'session_id': session_id,
                'status': mapped_status,
                'is_verified': status == 'completed' and verification_result.get('overall_result') == 'pass',
                'verification_details': verification_result,
                'timestamp': webhook_data.get('timestamp'),
                'raw_data': webhook_data
            }
            
        except Exception as e:
            logger.error(f"Error al procesar webhook de DIDIT: {str(e)}")
            return {
                'error': str(e),
                'raw_data': webhook_data
            } 