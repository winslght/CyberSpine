"""与平台无关的领域模型和基础服务。"""

from .event_queue import DurableEventQueue
from .gateway_errors import GatewayRejected, GatewayRejectionCode
from .message_limits import MessageLimits
from .neural_gateway import NeuralSignalGateway, PeripheralRegistration
from .neural_message import NeuralMessage
from .plugin_manifest import PluginManifest, PluginRuntimeSpec, load_manifest
from .plugin_registration import PluginGrant, PluginSession, RegistrationRegistry
from .schema_validation import validate_payload

__all__ = ["DurableEventQueue", "GatewayRejected", "GatewayRejectionCode", "NeuralMessage",
           "NeuralSignalGateway", "PeripheralRegistration", "PluginGrant", "PluginManifest",
           "PluginRuntimeSpec", "PluginSession", "RegistrationRegistry", "load_manifest", "validate_payload",
           "MessageLimits"]
