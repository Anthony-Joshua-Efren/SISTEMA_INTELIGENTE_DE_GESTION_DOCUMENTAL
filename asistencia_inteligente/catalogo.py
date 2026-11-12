"""
Conocimiento base del asistente: palabras clave por categoría y por etiqueta.

Se construyó a partir del cuestionario aplicado al Assistant IT Manager
del hotel (sistemas Opera, Silverware, HotSOS, audio y CCTV; tipos de
documento como contratos, facturas, cotizaciones, certificados, etc.).

Las claves se comparan SIN acentos y en minúsculas. Si el administrador
crea una categoría o etiqueta nueva que no aparece aquí, el asistente
sigue funcionando con su nombre, su descripción y los documentos que ya
tiene asignados.
"""

PALABRAS_CLAVE_CATEGORIA = {
    "administracion": [
        "administrativo", "oficio", "memorandum", "circular", "acta",
        "minuta", "solicitud", "proceso interno", "lineamiento",
    ],
    "finanzas": [
        "factura", "cotizacion", "presupuesto", "pago", "cobro",
        "contabilidad", "fiscal", "impuesto", "cfdi", "estado de cuenta",
        "orden de compra", "gasto", "costo",
    ],
    "recursos humanos": [
        "empleado", "colaborador", "nomina", "contratacion", "vacaciones",
        "capacitacion", "reclutamiento", "incidencia", "prestaciones",
    ],
    "tecnologia": [
        "opera", "silverware", "hotsos", "cctv", "servidor", "red",
        "ip", "switch", "router", "firewall", "respaldo", "backup",
        "configuracion", "licencia", "software", "hardware", "sistema",
        "ticket", "wifi", "audio", "pms", "vlan", "dns", "antivirus",
    ],
    "seguridad": [
        "seguridad", "camara", "acceso", "vigilancia", "emergencia",
        "evacuacion", "proteccion civil", "alarma", "incidente",
        "bitacora de seguridad",
    ],
    "mantenimiento e ingenieria": [
        "mantenimiento", "instalacion", "equipo", "hvac", "elevador",
        "plomeria", "electrico", "caldera", "preventivo", "correctivo",
        "garantia", "refaccion", "planta de emergencia",
    ],
    "alimentos y bebidas": [
        "restaurante", "bar", "banquete", "menu", "cocina", "receta",
        "alimentos", "bebidas", "comanda", "evento", "chef",
    ],
    "comercial y marketing": [
        "ventas", "marketing", "promocion", "campana", "cliente",
        "reservaciones", "tarifa", "publicidad", "redes sociales",
        "comercial",
    ],
    "cumplimiento y normatividad": [
        "norma", "normatividad", "politica", "cumplimiento", "auditoria",
        "regulatorio", "iso", "nom", "certificado", "licencia de operacion",
        "privacidad", "proteccion de datos",
    ],
}

PALABRAS_CLAVE_ETIQUETA = {
    "opera": ["opera", "oracle", "pms", "hotel property management"],
    "silverware": ["silverware", "punto de venta", "pos", "comanda"],
    "hotsos": ["hotsos", "ordenes de trabajo", "orden de servicio"],
    "cctv": ["cctv", "camara", "videovigilancia", "dvr", "nvr", "grabacion"],
    "audio": ["audio", "sonido", "bocina", "amplificador", "microfono"],
    "red": ["red", "switch", "router", "vlan", "wifi", "topologia"],
    "direcciones ip": ["ip", "direccionamiento", "subred", "mascara", "dhcp"],
    "servidores": ["servidor", "vmware", "virtualizacion", "hyper v", "nas"],
    "respaldos": ["respaldo", "backup", "restauracion", "recuperacion"],
    "proveedores": ["proveedor", "proveedores", "distribuidor"],
    "contratos": ["contrato", "clausula", "vigencia", "arrendamiento"],
    "licencias": ["licencia", "licenciamiento", "suscripcion", "renovacion"],
    "certificados": ["certificado", "certificacion", "ssl", "acreditacion"],
    "garantias": ["garantia", "poliza", "soporte extendido"],
    "mantenimiento": ["mantenimiento", "preventivo", "correctivo", "bitacora"],
    "inventario": ["inventario", "activo fijo", "numero de serie", "equipos"],
    "diagramas": ["diagrama", "topologia", "plano", "esquema"],
    "instructivos": ["instructivo", "guia", "paso a paso", "como"],
    "cotizaciones": ["cotizacion", "propuesta economica", "presupuesto"],
    "facturas": ["factura", "cfdi", "folio fiscal"],
}

# Etiquetas iniciales que se crean con el comando `seed_etiquetas`.
ETIQUETAS_INICIALES = [
    ("Opera", "Documentos del sistema Opera (PMS)."),
    ("Silverware", "Documentos del sistema Silverware (punto de venta)."),
    ("HotSOS", "Documentos del sistema HotSOS (órdenes de trabajo)."),
    ("CCTV", "Cámaras y videovigilancia."),
    ("Audio", "Sistemas de audio y sonido."),
    ("Red", "Infraestructura y configuración de red."),
    ("Direcciones IP", "Direccionamiento y subredes."),
    ("Servidores", "Servidores y virtualización."),
    ("Respaldos", "Respaldos y recuperación de información."),
    ("Proveedores", "Documentación de proveedores."),
    ("Contratos", "Contratos y su vigencia."),
    ("Licencias", "Licencias y suscripciones."),
    ("Certificados", "Certificados y certificaciones."),
    ("Garantías", "Garantías y pólizas."),
    ("Mantenimiento", "Mantenimientos preventivos y correctivos."),
    ("Inventario", "Inventarios de equipos y activos."),
    ("Diagramas", "Diagramas de red y de infraestructura."),
    ("Instructivos", "Instructivos y guías paso a paso."),
    ("Cotizaciones", "Cotizaciones y propuestas económicas."),
    ("Facturas", "Facturas y comprobantes fiscales."),
]
