import os
import tempfile
from typing import Dict, List, Any
import pandas as pd
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import logging
from starlette.concurrency import run_in_threadpool

from ..core.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting data to various formats"""
    
    def __init__(self):
        self.supported_formats = ['csv', 'xlsx', 'json', 'pdf']
    
    async def export_data(self, data: Dict[str, pd.DataFrame], format_type: str, job_id: str) -> List[str]:
        """Export data to specified format"""
        try:
            export_dir = os.path.join(settings.EXPORT_DIR, job_id)
            os.makedirs(export_dir, exist_ok=True)
            
            exported_files = []
            
            if format_type == 'csv':
                exported_files = await run_in_threadpool(self._export_csv, data, export_dir)
            elif format_type == 'xlsx':
                exported_files = await run_in_threadpool(self._export_xlsx, data, export_dir)
            elif format_type == 'json':
                exported_files = await run_in_threadpool(self._export_json, data, export_dir)
            elif format_type == 'pdf':
                exported_files = await run_in_threadpool(self._export_pdf, data, export_dir)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            logger.info(f"Exported {len(exported_files)} files for job {job_id} in {format_type} format")
            return exported_files
            
        except Exception as e:
            logger.error(f"Export error for job {job_id}: {str(e)}")
            raise
    
    def _export_csv(self, data: Dict[str, pd.DataFrame], export_dir: str) -> List[str]:
        """Export data as CSV files"""
        files = []
        
        for table_name, df in data.items():
            filename = f"{table_name}.csv"
            file_path = os.path.join(export_dir, filename)
            
            # Export to CSV with UTF-8 encoding
            df.to_csv(file_path, index=False, encoding='utf-8')
            files.append(file_path)
            logger.debug(f"Exported {table_name} to CSV: {len(df)} rows")
        
        return files
    
    def _export_xlsx(self, data: Dict[str, pd.DataFrame], export_dir: str) -> List[str]:
        """Export data as Excel file with multiple sheets"""
        filename = "database_export.xlsx"
        file_path = os.path.join(export_dir, filename)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for table_name, df in data.items():
                # Excel sheet names have character limits and restrictions
                sheet_name = self._sanitize_sheet_name(table_name)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.debug(f"Exported {table_name} to Excel sheet: {len(df)} rows")
        
        return [file_path]
    
    def _export_json(self, data: Dict[str, pd.DataFrame], export_dir: str) -> List[str]:
        """Export data as JSON files"""
        files = []
        
        for table_name, df in data.items():
            filename = f"{table_name}.json"
            file_path = os.path.join(export_dir, filename)
            
            # Convert DataFrame to JSON with proper formatting
            json_data = {
                "table_name": table_name,
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient='records')
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            files.append(file_path)
            logger.debug(f"Exported {table_name} to JSON: {len(df)} rows")
        
        return files
    
    def _export_pdf(self, data: Dict[str, pd.DataFrame], export_dir: str) -> List[str]:
        """Export data as PDF files"""
        files = []
        
        for table_name, df in data.items():
            filename = f"{table_name}.pdf"
            file_path = os.path.join(export_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            story = []
            
            # Setup styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.darkblue,
                alignment=1  # Center alignment
            )
            
            # Add title
            title = Paragraph(f"Table: {table_name}", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Add table info
            info_text = f"Rows: {len(df)} | Columns: {len(df.columns)}"
            info = Paragraph(info_text, styles['Normal'])
            story.append(info)
            story.append(Spacer(1, 12))
            
            # Prepare table data for PDF
            if len(df) > 0:
                # Limit rows for PDF (to avoid huge files)
                max_rows = 1000
                if len(df) > max_rows:
                    df_limited = df.head(max_rows)
                    warning = Paragraph(
                        f"<b>Note:</b> Only showing first {max_rows} rows of {len(df)} total rows.",
                        styles['Normal']
                    )
                    story.append(warning)
                    story.append(Spacer(1, 12))
                else:
                    df_limited = df
                
                # Convert DataFrame to table data
                table_data = [df_limited.columns.tolist()]  # Header
                
                # Add data rows (convert all to strings and limit length)
                for _, row in df_limited.iterrows():
                    row_data = []
                    for val in row:
                        str_val = str(val) if val is not None else ""
                        # Limit cell content length
                        if len(str_val) > 50:
                            str_val = str_val[:47] + "..."
                        row_data.append(str_val)
                    table_data.append(row_data)
                
                # Create PDF table
                pdf_table = Table(table_data)
                pdf_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                
                story.append(pdf_table)
            else:
                no_data = Paragraph("No data available in this table.", styles['Normal'])
                story.append(no_data)
            
            # Build PDF
            doc.build(story)
            files.append(file_path)
            logger.debug(f"Exported {table_name} to PDF: {len(df)} rows")
        
        return files
    
    def _sanitize_sheet_name(self, name: str) -> str:
        """Sanitize sheet name for Excel compatibility"""
        # Excel sheet name restrictions
        invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
        sanitized = name
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length (Excel limit is 31 characters)
        if len(sanitized) > 31:
            sanitized = sanitized[:31]
        
        return sanitized
