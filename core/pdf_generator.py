import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
# from svglib.svglib import svg2rlg # In caso si debbano caricare SVG da Locale/Url

def genera_pdf_pratica(
    pratica_id: str, 
    tipo: str, 
    richiedente: str, 
    data_creazione: str, 
    stato_attuale: str,
    dati_json: dict,
    header_url: str = None,
    footer_url: str = None
) -> bytes:
    """
    Genera un PDF di riepilogo utilizzando ReportLab.
    Restituisce i bytes del PDF.
    """
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []
    
    # Intestazione (Placeholder Testuale se manca logo SVG/PNG)
    # TODO: Logica per scaricare o renderizzare l'immagine dall'URL di Drive
    elements.append(Paragraph("Dipartimento DIMES - Università della Calabria", title_style))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph(f"Riepilogo Pratica: {pratica_id}", heading_style))
    elements.append(Spacer(1, 10))
    
    # Tabella Dati Generali
    gen_data = [
        ["Tipo Pratica", tipo],
        ["Richiedente", richiedente],
        ["Data Creazione", data_creazione],
        ["Stato Attuale", stato_attuale],
    ]
    t1 = Table(gen_data, colWidths=[150, 300])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 20))
    
    # Tabella Dati Dinamici Form JSON
    elements.append(Paragraph("Dettagli Specifici", heading_style))
    elements.append(Spacer(1, 10))
    
    spec_data = []
    for k, v in dati_json.items():
         key_str = str(k).replace('_', ' ').title()
         val_str = str(v)
         # Per stringhe lunghe, usiamo un Paragraph nella cella
         p_val = Paragraph(val_str, normal_style)
         spec_data.append([key_str, p_val])
         
    if spec_data:
        t2 = Table(spec_data, colWidths=[150, 300])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(t2)
        
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generato dal Sistema HipA il {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))

    # Build the PDF
    doc.build(elements)
    
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    return pdf_bytes
