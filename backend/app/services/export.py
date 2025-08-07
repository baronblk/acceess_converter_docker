"""
Export service for converting Access data to various formats
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from fpdf import FPDF
import zipfile
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger, logger_setup
from app.models import ExportFormat, JobProgress, JobStatus, ResultFile
from app.services.ucanaccess import UCanAccessService
from app.services.jobs import job_service
from app.utils import create_export_directory, sanitize_filename

logger = get_logger(__name__)


class ExportService:
    """Service for exporting Access database tables to various formats"""
    
    def __init__(self):
        self.ucanaccess = UCanAccessService()
    
    def export_table_csv(self, df: pd.DataFrame, output_path: Path) -> bool:
        """Export DataFrame to CSV format"""
        try:
            df.to_csv(
                output_path,
                index=False,
                encoding='utf-8-sig',  # UTF-8 with BOM
                sep=';',  # German/European standard
                quoting=csv.QUOTE_ALL,
                lineterminator='\n'
            )
            
            logger.info("CSV export completed", 
                       output_path=str(output_path),
                       rows=len(df))
            return True
            
        except Exception as e:
            logger.error("CSV export failed", 
                        output_path=str(output_path),
                        error=str(e))
            return False
    
    def export_table_xlsx(self, df: pd.DataFrame, output_path: Path, table_name: str) -> bool:
        """Export DataFrame to XLSX format"""
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Use table name as sheet name (sanitized)
                sheet_name = sanitize_filename(table_name)[:31]  # Excel sheet name limit
                
                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                    freeze_panes=(1, 0)  # Freeze header row
                )
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Max width 50
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info("XLSX export completed", 
                       output_path=str(output_path),
                       rows=len(df),
                       table_name=table_name)
            return True
            
        except Exception as e:
            logger.error("XLSX export failed", 
                        output_path=str(output_path),
                        table_name=table_name,
                        error=str(e))
            return False
    
    def export_table_json(self, df: pd.DataFrame, output_path: Path) -> bool:
        """Export DataFrame to JSON format"""
        try:
            # Convert DataFrame to JSON with records orientation
            json_data = df.to_json(
                orient='records',
                force_ascii=False,
                date_format='iso',
                indent=2
            )
            
            # Write to file with UTF-8 encoding
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            
            logger.info("JSON export completed", 
                       output_path=str(output_path),
                       rows=len(df))
            return True
            
        except Exception as e:
            logger.error("JSON export failed", 
                        output_path=str(output_path),
                        error=str(e))
            return False
    
    def export_table_pdf(self, df: pd.DataFrame, output_path: Path, table_name: str) -> bool:
        """Export DataFrame to PDF format"""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            
            # Title
            pdf.cell(0, 10, f'Table: {table_name}', ln=True, align='C')
            pdf.ln(10)
            
            # Set font for table
            pdf.set_font('Arial', '', 8)
            
            # Calculate column widths
            page_width = pdf.w - 20  # Margins
            col_count = len(df.columns)
            col_width = page_width / col_count if col_count > 0 else 20
            
            # Limit column width
            if col_width > 40:
                col_width = 40
            elif col_width < 15:
                col_width = 15
            
            # Table headers
            pdf.set_font('Arial', 'B', 8)
            for col in df.columns:
                pdf.cell(col_width, 7, str(col)[:20], 1, 0, 'C')  # Limit header length
            pdf.ln()
            
            # Table data
            pdf.set_font('Arial', '', 7)
            row_count = 0
            max_rows_per_page = 35
            
            for _, row in df.iterrows():
                if row_count >= max_rows_per_page:
                    pdf.add_page()
                    row_count = 0
                    
                    # Repeat headers on new page
                    pdf.set_font('Arial', 'B', 8)
                    for col in df.columns:
                        pdf.cell(col_width, 7, str(col)[:20], 1, 0, 'C')
                    pdf.ln()
                    pdf.set_font('Arial', '', 7)
                
                for value in row:
                    # Convert value to string and limit length
                    cell_value = str(value) if pd.notna(value) else ''
                    if len(cell_value) > 25:
                        cell_value = cell_value[:22] + '...'
                    
                    pdf.cell(col_width, 6, cell_value, 1, 0, 'L')
                
                pdf.ln()
                row_count += 1
            
            # Add metadata
            pdf.ln(10)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 5, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=True)
            pdf.cell(0, 5, f'Total rows: {len(df)}', ln=True)
            pdf.cell(0, 5, f'Total columns: {len(df.columns)}', ln=True)
            
            # Save PDF
            pdf.output(str(output_path))
            
            logger.info("PDF export completed", 
                       output_path=str(output_path),
                       rows=len(df),
                       table_name=table_name)
            return True
            
        except Exception as e:
            logger.error("PDF export failed", 
                        output_path=str(output_path),
                        table_name=table_name,
                        error=str(e))
            return False
    
    def export_table(
        self, 
        df: pd.DataFrame, 
        table_name: str, 
        format: ExportFormat, 
        output_dir: Path
    ) -> Optional[ResultFile]:
        """Export a single table to the specified format"""
        
        # Generate output filename
        safe_table_name = sanitize_filename(table_name)
        file_extensions = {
            ExportFormat.CSV: '.csv',
            ExportFormat.XLSX: '.xlsx',
            ExportFormat.JSON: '.json',
            ExportFormat.PDF: '.pdf'
        }
        
        filename = f"{safe_table_name}{file_extensions[format]}"
        output_path = output_dir / filename
        
        # Export based on format
        success = False
        if format == ExportFormat.CSV:
            success = self.export_table_csv(df, output_path)
        elif format == ExportFormat.XLSX:
            success = self.export_table_xlsx(df, output_path, table_name)
        elif format == ExportFormat.JSON:
            success = self.export_table_json(df, output_path)
        elif format == ExportFormat.PDF:
            success = self.export_table_pdf(df, output_path, table_name)
        
        if success and output_path.exists():
            # Create result file info
            file_size = output_path.stat().st_size
            download_url = f"/api/jobs/{{job_id}}/download/{table_name}"
            
            return ResultFile(
                table_name=table_name,
                filename=filename,
                format=format,
                size=file_size,
                download_url=download_url
            )
        
        return None
    
    def create_results_zip(self, job_id: str, export_dir: Path) -> Optional[Path]:
        """Create ZIP file containing all exported files"""
        try:
            zip_filename = f"{job_id}_export.zip"
            zip_path = export_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0
                
                for file_path in export_dir.rglob('*'):
                    if file_path.is_file() and file_path != zip_path:
                        # Add file to zip with relative path
                        arcname = file_path.relative_to(export_dir)
                        zipf.write(file_path, arcname)
                        file_count += 1
                
                logger.info("ZIP file created", 
                           zip_path=str(zip_path),
                           file_count=file_count)
                
                return zip_path if file_count > 0 else None
                
        except Exception as e:
            logger.error("Failed to create ZIP file", 
                        job_id=job_id,
                        export_dir=str(export_dir),
                        error=str(e))
            return None


def process_conversion_job(job_id: str):
    """
    Main function to process a conversion job
    This is the function that gets enqueued by RQ
    """
    # Set up logging context for this job
    logger_setup.set_request_context(job_id=job_id)
    
    logger.info("Starting conversion job", job_id=job_id)
    
    try:
        # Get job data
        job_data = job_service._get_job_data(job_id)
        if not job_data:
            raise Exception("Job data not found")
        
        # Update job status to running
        job_service.update_job_progress(
            job_id,
            JobProgress(
                percentage=0,
                completed_tables=0,
                total_tables=len(job_data.selected_tables),
                message="Starting conversion..."
            ),
            JobStatus.RUNNING
        )
        
        # Create export directory
        export_dir = create_export_directory(job_id)
        
        # Initialize services
        export_service = ExportService()
        
        # Connect to Access database
        logger.info("Connecting to Access database", file_path=job_data.file_path)
        export_service.ucanaccess.connect(job_data.file_path)
        
        try:
            completed_tables = 0
            total_tables = len(job_data.selected_tables)
            
            # Process each selected table
            for table_name in job_data.selected_tables:
                try:
                    logger.info("Processing table", table_name=table_name)
                    
                    # Update progress
                    progress_percentage = (completed_tables / total_tables) * 100
                    job_service.update_job_progress(
                        job_id,
                        JobProgress(
                            current_table=table_name,
                            completed_tables=completed_tables,
                            total_tables=total_tables,
                            percentage=progress_percentage,
                            message=f"Processing table: {table_name}"
                        )
                    )
                    
                    # Read table data
                    df = export_service.ucanaccess.read_table(table_name)
                    
                    # Export table
                    result_file = export_service.export_table(
                        df, 
                        table_name, 
                        job_data.format, 
                        export_dir
                    )
                    
                    if result_file:
                        # Add result file to job
                        job_service.add_result_file(job_id, result_file)
                        completed_tables += 1
                        
                        logger.info("Table exported successfully", 
                                   table_name=table_name,
                                   rows=len(df),
                                   format=job_data.format.value)
                    else:
                        logger.error("Failed to export table", table_name=table_name)
                
                except Exception as e:
                    logger.error("Error processing table", 
                                table_name=table_name,
                                error=str(e))
                    # Continue with next table instead of failing entire job
                    continue
            
            # Create ZIP file with all results
            logger.info("Creating ZIP file with all results")
            zip_path = export_service.create_results_zip(job_id, export_dir)
            
            # Mark job as completed
            job_service.update_job_progress(
                job_id,
                JobProgress(
                    completed_tables=completed_tables,
                    total_tables=total_tables,
                    percentage=100.0,
                    message=f"Conversion completed. {completed_tables}/{total_tables} tables processed."
                ),
                JobStatus.COMPLETED
            )
            
            logger.info("Conversion job completed successfully", 
                       job_id=job_id,
                       completed_tables=completed_tables,
                       total_tables=total_tables)
        
        finally:
            # Always disconnect from database
            export_service.ucanaccess.disconnect()
    
    except Exception as e:
        logger.error("Conversion job failed", job_id=job_id, error=str(e))
        
        # Mark job as failed
        job_service.mark_job_failed(job_id, str(e))
        
        raise  # Re-raise for RQ to handle


# Global export service instance
export_service = ExportService()
