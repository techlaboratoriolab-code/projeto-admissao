import json

# Estrutura completa do arquivo Figma
figma_file = {
    "name": "Sistema de Visualização de Laudos - LAB",
    "version": "1.0",
    "document": {
        "id": "0:0",
        "name": "Document",
        "type": "DOCUMENT",
        "children": [
            {
                "id": "1:1",
                "name": "Página Principal - Sistema LAB",
                "type": "CANVAS",
                "backgroundColor": {"r": 0.95, "g": 0.95, "b": 0.95, "a": 1},
                "children": [
                    # Frame 1 - Tela com Pedido Médico
                    {
                        "id": "2:1",
                        "name": "Tela 01 - Pedido Médico",
                        "type": "FRAME",
                        "width": 1920,
                        "height": 1080,
                        "x": 0,
                        "y": 0,
                        "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                        "children": [
                            # Card Esquerdo - Dados do Paciente
                            {
                                "id": "3:1",
                                "name": "Card - Dados do Paciente",
                                "type": "FRAME",
                                "width": 480,
                                "height": 1080,
                                "x": 0,
                                "y": 0,
                                "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                "effects": [
                                    {
                                        "type": "DROP_SHADOW",
                                        "color": {"r": 0, "g": 0, "b": 0, "a": 0.08},
                                        "offset": {"x": 2, "y": 0},
                                        "radius": 12,
                                        "visible": True
                                    }
                                ],
                                "children": [
                                    # Logo LAB
                                    {
                                        "id": "4:1",
                                        "name": "Logo LAB",
                                        "type": "RECTANGLE",
                                        "width": 120,
                                        "height": 60,
                                        "x": 32,
                                        "y": 32,
                                        "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0.4, "b": 0.8, "a": 1}}],
                                        "cornerRadius": 8
                                    },
                                    # Título - Dados do Paciente
                                    {
                                        "id": "4:2",
                                        "name": "Título - DADOS DO PACIENTE",
                                        "type": "TEXT",
                                        "characters": "📋 DADOS DO PACIENTE",
                                        "x": 32,
                                        "y": 120,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    # Nome do Paciente
                                    {
                                        "id": "4:3",
                                        "name": "Label - Nome",
                                        "type": "TEXT",
                                        "characters": "Nome Completo",
                                        "x": 32,
                                        "y": 180,
                                        "fontSize": 12,
                                        "fontWeight": 500,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}]
                                    },
                                    {
                                        "id": "4:4",
                                        "name": "Valor - Nome",
                                        "type": "TEXT",
                                        "characters": "Maria Silva Santos",
                                        "x": 32,
                                        "y": 200,
                                        "fontSize": 16,
                                        "fontWeight": 600,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    # Idade
                                    {
                                        "id": "4:5",
                                        "name": "Label - Idade",
                                        "type": "TEXT",
                                        "characters": "Idade",
                                        "x": 32,
                                        "y": 250,
                                        "fontSize": 12,
                                        "fontWeight": 500,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}]
                                    },
                                    {
                                        "id": "4:6",
                                        "name": "Valor - Idade",
                                        "type": "TEXT",
                                        "characters": "45 anos",
                                        "x": 32,
                                        "y": 270,
                                        "fontSize": 16,
                                        "fontWeight": 400,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    # Data de Nascimento
                                    {
                                        "id": "4:7",
                                        "name": "Label - Data Nascimento",
                                        "type": "TEXT",
                                        "characters": "Data de Nascimento",
                                        "x": 32,
                                        "y": 310,
                                        "fontSize": 12,
                                        "fontWeight": 500,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}]
                                    },
                                    {
                                        "id": "4:8",
                                        "name": "Valor - Data Nascimento",
                                        "type": "TEXT",
                                        "characters": "15/03/1980",
                                        "x": 32,
                                        "y": 330,
                                        "fontSize": 16,
                                        "fontWeight": 400,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    # Divisor
                                    {
                                        "id": "4:9",
                                        "name": "Divisor 1",
                                        "type": "RECTANGLE",
                                        "width": 416,
                                        "height": 1,
                                        "x": 32,
                                        "y": 380,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1}}]
                                    },
                                    # Seção Prontuário
                                    {
                                        "id": "4:10",
                                        "name": "Título - PRONTUÁRIO",
                                        "type": "TEXT",
                                        "characters": "📄 PRONTUÁRIO",
                                        "x": 32,
                                        "y": 410,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    {
                                        "id": "4:11",
                                        "name": "Valor - Número Prontuário",
                                        "type": "TEXT",
                                        "characters": "2024-00123456",
                                        "x": 32,
                                        "y": 450,
                                        "fontSize": 20,
                                        "fontWeight": 600,
                                        "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0.4, "b": 0.8, "a": 1}}]
                                    },
                                    # Divisor
                                    {
                                        "id": "4:12",
                                        "name": "Divisor 2",
                                        "type": "RECTANGLE",
                                        "width": 416,
                                        "height": 1,
                                        "x": 32,
                                        "y": 500,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1}}]
                                    },
                                    # Seção Convênio
                                    {
                                        "id": "4:13",
                                        "name": "Título - CONVÊNIO",
                                        "type": "TEXT",
                                        "characters": "🏥 CONVÊNIO",
                                        "x": 32,
                                        "y": 530,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    {
                                        "id": "4:14",
                                        "name": "Valor - Convênio",
                                        "type": "TEXT",
                                        "characters": "Unimed Brasília",
                                        "x": 32,
                                        "y": 570,
                                        "fontSize": 16,
                                        "fontWeight": 400,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    # Divisor
                                    {
                                        "id": "4:15",
                                        "name": "Divisor 3",
                                        "type": "RECTANGLE",
                                        "width": 416,
                                        "height": 1,
                                        "x": 32,
                                        "y": 620,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1}}]
                                    },
                                    # Médico Solicitante
                                    {
                                        "id": "4:16",
                                        "name": "Título - MÉDICO",
                                        "type": "TEXT",
                                        "characters": "👨‍⚕️ MÉDICO SOLICITANTE",
                                        "x": 32,
                                        "y": 650,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    {
                                        "id": "4:17",
                                        "name": "Valor - Nome Médico",
                                        "type": "TEXT",
                                        "characters": "Dr. João Pedro Oliveira",
                                        "x": 32,
                                        "y": 690,
                                        "fontSize": 16,
                                        "fontWeight": 600,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    {
                                        "id": "4:18",
                                        "name": "Valor - CRM",
                                        "type": "TEXT",
                                        "characters": "CRM: 12345-DF",
                                        "x": 32,
                                        "y": 715,
                                        "fontSize": 14,
                                        "fontWeight": 400,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}]
                                    },
                                    # Divisor
                                    {
                                        "id": "4:19",
                                        "name": "Divisor 4",
                                        "type": "RECTANGLE",
                                        "width": 416,
                                        "height": 1,
                                        "x": 32,
                                        "y": 760,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1}}]
                                    },
                                    # Atendimento
                                    {
                                        "id": "4:20",
                                        "name": "Título - ATENDIMENTO",
                                        "type": "TEXT",
                                        "characters": "📅 ATENDIMENTO",
                                        "x": 32,
                                        "y": 790,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    {
                                        "id": "4:21",
                                        "name": "Label - Data Coleta",
                                        "type": "TEXT",
                                        "characters": "Data da Coleta",
                                        "x": 32,
                                        "y": 830,
                                        "fontSize": 12,
                                        "fontWeight": 500,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1}}]
                                    },
                                    {
                                        "id": "4:22",
                                        "name": "Valor - Data Coleta",
                                        "type": "TEXT",
                                        "characters": "20/12/2024 às 08:30",
                                        "x": 32,
                                        "y": 850,
                                        "fontSize": 16,
                                        "fontWeight": 400,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}]
                                    },
                                    # Divisor
                                    {
                                        "id": "4:23",
                                        "name": "Divisor 5",
                                        "type": "RECTANGLE",
                                        "width": 416,
                                        "height": 1,
                                        "x": 32,
                                        "y": 900,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1}}]
                                    },
                                    # Status
                                    {
                                        "id": "4:24",
                                        "name": "Título - STATUS",
                                        "type": "TEXT",
                                        "characters": "✅ STATUS",
                                        "x": 32,
                                        "y": 930,
                                        "fontSize": 18,
                                        "fontWeight": 700,
                                        "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                    },
                                    {
                                        "id": "4:25",
                                        "name": "Badge - Status Liberado",
                                        "type": "FRAME",
                                        "width": 150,
                                        "height": 36,
                                        "x": 32,
                                        "y": 970,
                                        "backgroundColor": {"r": 0.2, "g": 0.8, "b": 0.4, "a": 0.15},
                                        "cornerRadius": 8,
                                        "children": [
                                            {
                                                "id": "4:26",
                                                "name": "Texto - Liberado",
                                                "type": "TEXT",
                                                "characters": "Laudo Liberado",
                                                "x": 20,
                                                "y": 8,
                                                "fontSize": 14,
                                                "fontWeight": 600,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.6, "b": 0.2, "a": 1}}]
                                            }
                                        ]
                                    }
                                ]
                            },
                            # Área Direita - Documentos
                            {
                                "id": "5:1",
                                "name": "Área - Visualização de Documentos",
                                "type": "FRAME",
                                "width": 1440,
                                "height": 1080,
                                "x": 480,
                                "y": 0,
                                "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                                "children": [
                                    # Header
                                    {
                                        "id": "6:1",
                                        "name": "Header - Documentos",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 80,
                                        "x": 30,
                                        "y": 30,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "effects": [
                                            {
                                                "type": "DROP_SHADOW",
                                                "color": {"r": 0, "g": 0, "b": 0, "a": 0.05},
                                                "offset": {"x": 0, "y": 2},
                                                "radius": 8,
                                                "visible": True
                                            }
                                        ],
                                        "children": [
                                            {
                                                "id": "6:2",
                                                "name": "Título - DOCUMENTOS E EXAMES",
                                                "type": "TEXT",
                                                "characters": "DOCUMENTOS E EXAMES",
                                                "x": 24,
                                                "y": 28,
                                                "fontSize": 20,
                                                "fontWeight": 700,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                            },
                                            {
                                                "id": "6:3",
                                                "name": "Badge - Tipo Documento",
                                                "type": "FRAME",
                                                "width": 180,
                                                "height": 32,
                                                "x": 1176,
                                                "y": 24,
                                                "backgroundColor": {"r": 0, "g": 0.4, "b": 0.8, "a": 0.1},
                                                "cornerRadius": 6,
                                                "children": [
                                                    {
                                                        "id": "6:4",
                                                        "name": "Texto - Pedido Médico",
                                                        "type": "TEXT",
                                                        "characters": "📋 Pedido Médico",
                                                        "x": 16,
                                                        "y": 6,
                                                        "fontSize": 13,
                                                        "fontWeight": 600,
                                                        "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0.4, "b": 0.8, "a": 1}}]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    # Container da Imagem do Documento
                                    {
                                        "id": "6:5",
                                        "name": "Container - Imagem Documento",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 940,
                                        "x": 30,
                                        "y": 130,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "effects": [
                                            {
                                                "type": "DROP_SHADOW",
                                                "color": {"r": 0, "g": 0, "b": 0, "a": 0.08},
                                                "offset": {"x": 0, "y": 4},
                                                "radius": 16,
                                                "visible": True
                                            }
                                        ],
                                        "children": [
                                            {
                                                "id": "6:6",
                                                "name": "Placeholder - Imagem Pedido",
                                                "type": "RECTANGLE",
                                                "width": 1300,
                                                "height": 860,
                                                "x": 40,
                                                "y": 40,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.96, "g": 0.96, "b": 0.96, "a": 1}}],
                                                "cornerRadius": 8
                                            },
                                            {
                                                "id": "6:7",
                                                "name": "Texto - Placeholder",
                                                "type": "TEXT",
                                                "characters": "Imagem do Pedido Médico\n\nArraste sua imagem aqui ou\nsubstitua este placeholder",
                                                "x": 540,
                                                "y": 400,
                                                "fontSize": 18,
                                                "fontWeight": 400,
                                                "textAlignHorizontal": "CENTER",
                                                "fills": [{"type": "SOLID", "color": {"r": 0.6, "g": 0.6, "b": 0.6, "a": 1}}]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # Frame 2 - Tela com Laudo
                    {
                        "id": "2:2",
                        "name": "Tela 02 - Laudo",
                        "type": "FRAME",
                        "width": 1920,
                        "height": 1080,
                        "x": 2000,
                        "y": 0,
                        "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                        "children": [
                            # Reutiliza o mesmo Card Esquerdo (referência ao componente)
                            {
                                "id": "3:2",
                                "name": "Card - Dados do Paciente (Instância)",
                                "type": "INSTANCE",
                                "componentId": "3:1",
                                "width": 480,
                                "height": 1080,
                                "x": 0,
                                "y": 0
                            },
                            # Área Direita - Laudo
                            {
                                "id": "5:2",
                                "name": "Área - Visualização de Documentos",
                                "type": "FRAME",
                                "width": 1440,
                                "height": 1080,
                                "x": 480,
                                "y": 0,
                                "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                                "children": [
                                    {
                                        "id": "7:1",
                                        "name": "Header - Documentos",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 80,
                                        "x": 30,
                                        "y": 30,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "children": [
                                            {
                                                "id": "7:2",
                                                "name": "Título - DOCUMENTOS E EXAMES",
                                                "type": "TEXT",
                                                "characters": "DOCUMENTOS E EXAMES",
                                                "x": 24,
                                                "y": 28,
                                                "fontSize": 20,
                                                "fontWeight": 700,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                            },
                                            {
                                                "id": "7:3",
                                                "name": "Badge - Laudo",
                                                "type": "FRAME",
                                                "width": 140,
                                                "height": 32,
                                                "x": 1216,
                                                "y": 24,
                                                "backgroundColor": {"r": 0.2, "g": 0.8, "b": 0.4, "a": 0.1},
                                                "cornerRadius": 6,
                                                "children": [
                                                    {
                                                        "id": "7:4",
                                                        "name": "Texto - Laudo",
                                                        "type": "TEXT",
                                                        "characters": "📄 Laudo",
                                                        "x": 30,
                                                        "y": 6,
                                                        "fontSize": 13,
                                                        "fontWeight": 600,
                                                        "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.6, "b": 0.2, "a": 1}}]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "id": "7:5",
                                        "name": "Container - Imagem Laudo",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 940,
                                        "x": 30,
                                        "y": 130,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "children": [
                                            {
                                                "id": "7:6",
                                                "name": "Placeholder - Imagem Laudo",
                                                "type": "RECTANGLE",
                                                "width": 1300,
                                                "height": 860,
                                                "x": 40,
                                                "y": 40,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.96, "g": 0.96, "b": 0.96, "a": 1}}],
                                                "cornerRadius": 8
                                            },
                                            {
                                                "id": "7:7",
                                                "name": "Texto - Placeholder Laudo",
                                                "type": "TEXT",
                                                "characters": "Imagem do Laudo\n\nArraste sua imagem aqui",
                                                "x": 580,
                                                "y": 400,
                                                "fontSize": 18,
                                                "fontWeight": 400,
                                                "textAlignHorizontal": "CENTER",
                                                "fills": [{"type": "SOLID", "color": {"r": 0.6, "g": 0.6, "b": 0.6, "a": 1}}]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    # Frame 3 - Tela com Resultado de Exame
                    {
                        "id": "2:3",
                        "name": "Tela 03 - Resultado de Exame",
                        "type": "FRAME",
                        "width": 1920,
                        "height": 1080,
                        "x": 4000,
                        "y": 0,
                        "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                        "children": [
                            {
                                "id": "3:3",
                                "name": "Card - Dados do Paciente (Instância)",
                                "type": "INSTANCE",
                                "componentId": "3:1",
                                "width": 480,
                                "height": 1080,
                                "x": 0,
                                "y": 0
                            },
                            {
                                "id": "5:3",
                                "name": "Área - Visualização de Documentos",
                                "type": "FRAME",
                                "width": 1440,
                                "height": 1080,
                                "x": 480,
                                "y": 0,
                                "backgroundColor": {"r": 0.98, "g": 0.98, "b": 0.98, "a": 1},
                                "children": [
                                    {
                                        "id": "8:1",
                                        "name": "Header - Documentos",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 80,
                                        "x": 30,
                                        "y": 30,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "children": [
                                            {
                                                "id": "8:2",
                                                "name": "Título - DOCUMENTOS E EXAMES",
                                                "type": "TEXT",
                                                "characters": "DOCUMENTOS E EXAMES",
                                                "x": 24,
                                                "y": 28,
                                                "fontSize": 20,
                                                "fontWeight": 700,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1}}]
                                            },
                                            {
                                                "id": "8:3",
                                                "name": "Badge - Resultado",
                                                "type": "FRAME",
                                                "width": 180,
                                                "height": 32,
                                                "x": 1176,
                                                "y": 24,
                                                "backgroundColor": {"r": 0.6, "g": 0.2, "b": 0.8, "a": 0.1},
                                                "cornerRadius": 6,
                                                "children": [
                                                    {
                                                        "id": "8:4",
                                                        "name": "Texto - Resultado",
                                                        "type": "TEXT",
                                                        "characters": "🔬 Resultado Exame",
                                                        "x": 16,
                                                        "y": 6,
                                                        "fontSize": 13,
                                                        "fontWeight": 600,
                                                        "fills": [{"type": "SOLID", "color": {"r": 0.5, "g": 0.1, "b": 0.7, "a": 1}}]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "id": "8:5",
                                        "name": "Container - Imagem Resultado",
                                        "type": "FRAME",
                                        "width": 1380,
                                        "height": 940,
                                        "x": 30,
                                        "y": 130,
                                        "backgroundColor": {"r": 1, "g": 1, "b": 1, "a": 1},
                                        "cornerRadius": 12,
                                        "children": [
                                            {
                                                "id": "8:6",
                                                "name": "Placeholder - Imagem Resultado",
                                                "type": "RECTANGLE",
                                                "width": 1300,
                                                "height": 860,
                                                "x": 40,
                                                "y": 40,
                                                "fills": [{"type": "SOLID", "color": {"r": 0.96, "g": 0.96, "b": 0.96, "a": 1}}],
                                                "cornerRadius": 8
                                            },
                                            {
                                                "id": "8:7",
                                                "name": "Texto - Placeholder Resultado",
                                                "type": "TEXT",
                                                "characters": "Imagem do Resultado\n\nArraste sua imagem aqui",
                                                "x": 560,
                                                "y": 400,
                                                "fontSize": 18,
                                                "fontWeight": 400,
                                                "textAlignHorizontal": "CENTER",
                                                "fills": [{"type": "SOLID", "color": {"r": 0.6, "g": 0.6, "b": 0.6, "a": 1}}]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    },
    # Configuração de Protótipo (Auto-play)
    "prototypeStartNodeID": "2:1",
    "prototypeDevice": {
        "type": "PRESET",
        "preset": "DESKTOP"
    }
}

# Salvar arquivo JSON
with open('/home/claude/sistema_laudos_lab.json', 'w', encoding='utf-8') as f:
    json.dump(figma_file, f, indent=2, ensure_ascii=False)

