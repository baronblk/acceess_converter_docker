"""
Erweiterte Export-Services für Access Database Converter
- Pivot-Tabellen für Excel
- Schema-Export mit ER-Diagrammen  
- Query-Export und -Ausführung
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from io import StringIO

from ..core.logging import get_logger

logger = get_logger("export_advanced")


class PivotTableService:
    """Service für die Erstellung von Pivot-Tabellen in Excel"""
    
    @staticmethod
    def create_pivot_tables(data: Dict[str, pd.DataFrame], output_path: str) -> str:
        """
        Erstellt Excel-Datei mit Pivot-Tabellen
        
        Args:
            data: Dict mit Tabellennamen als Keys und DataFrames als Values
            output_path: Ausgabepfad für die Excel-Datei
            
        Returns:
            Pfad zur erstellten Excel-Datei
        """
        try:
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                for table_name, df in data.items():
                    if df.empty:
                        continue
                    
                    # Hauptdatenblatt
                    sheet_name = table_name[:31]  # Excel Sheet-Namen max 31 Zeichen
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Pivot-Tabelle erstellen falls möglich
                    pivot_sheet = PivotTableService._create_pivot_for_table(
                        df, table_name, writer, workbook
                    )
                    
                    if pivot_sheet:
                        logger.info(f"Pivot-Tabelle erstellt für {table_name}")
                
                logger.info(f"Excel mit Pivot-Tabellen erstellt: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Pivot-Tabellen: {e}")
            raise
    
    @staticmethod
    def _create_pivot_for_table(df: pd.DataFrame, table_name: str, 
                               writer: pd.ExcelWriter, workbook) -> Optional[str]:
        """
        Erstellt eine Pivot-Tabelle für eine einzelne Tabelle
        
        Args:
            df: DataFrame mit den Daten
            table_name: Name der Tabelle
            writer: Excel Writer
            workbook: Excel Workbook
            
        Returns:
            Name des Pivot-Sheets oder None
        """
        try:
            # Finde geeignete Spalten für Pivot
            text_columns = []
            numeric_columns = []
            
            for col in df.columns:
                if df[col].dtype in ['object', 'string']:
                    text_columns.append(col)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    numeric_columns.append(col)
            
            if not text_columns or not numeric_columns:
                logger.debug(f"Keine geeigneten Spalten für Pivot in {table_name}")
                return None
            
            # Erstelle Pivot-Sheet
            pivot_sheet_name = f"{table_name[:25]}_Pivot"
            worksheet = workbook.add_worksheet(pivot_sheet_name)
            
            # Einfaches Pivot: Erste Text-Spalte als Zeile, erste numerische als Wert
            row_field = text_columns[0]
            value_field = numeric_columns[0]
            
            # Erstelle Pivot-Daten
            pivot_data = df.groupby(row_field)[value_field].agg(['sum', 'count', 'mean']).round(2)
            
            # Schreibe Pivot-Daten
            headers = [row_field, f'{value_field}_Summe', f'{value_field}_Anzahl', f'{value_field}_Durchschnitt']
            
            # Header schreiben
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
            
            # Daten schreiben
            for row, (index, data) in enumerate(pivot_data.iterrows(), 1):
                worksheet.write(row, 0, str(index))
                worksheet.write(row, 1, data['sum'])
                worksheet.write(row, 2, data['count'])
                worksheet.write(row, 3, data['mean'])
            
            # Formatierung
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
            for col in range(len(headers)):
                worksheet.write(0, col, headers[col], header_format)
            
            logger.debug(f"Pivot-Sheet erstellt: {pivot_sheet_name}")
            return pivot_sheet_name
            
        except Exception as e:
            logger.warning(f"Fehler beim Erstellen der Pivot-Tabelle für {table_name}: {e}")
            return None


class QueryExportService:
    """Service für den Export von Access-Abfragen"""
    
    @staticmethod
    def export_queries_json(queries: Dict[str, str], output_path: str) -> str:
        """
        Exportiert Abfrage-Definitionen als JSON
        
        Args:
            queries: Dict mit Query-Namen als Keys und SQL als Values
            output_path: Ausgabepfad für die JSON-Datei
            
        Returns:
            Pfad zur erstellten JSON-Datei
        """
        try:
            queries_export = {
                "database_queries": queries,
                "export_timestamp": pd.Timestamp.now().isoformat(),
                "query_count": len(queries)
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(queries_export, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Abfragen exportiert: {len(queries)} Queries -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fehler beim Exportieren der Abfragen: {e}")
            raise
    
    @staticmethod
    def export_query_results(query_results: Dict[str, pd.DataFrame], 
                           output_dir: str, format: str = 'csv') -> List[str]:
        """
        Exportiert Abfrage-Ergebnisse als CSV oder Excel
        
        Args:
            query_results: Dict mit Query-Namen als Keys und DataFrames als Values
            output_dir: Ausgabeverzeichnis
            format: 'csv' oder 'xlsx'
            
        Returns:
            Liste der erstellten Dateipfade
        """
        created_files = []
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            for query_name, df in query_results.items():
                if df.empty:
                    continue
                
                # Sichere Dateinamen
                safe_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in query_name)
                
                if format.lower() == 'csv':
                    file_path = os.path.join(output_dir, f"query_{safe_name}.csv")
                    df.to_csv(file_path, index=False, encoding='utf-8')
                elif format.lower() == 'xlsx':
                    file_path = os.path.join(output_dir, f"query_{safe_name}.xlsx")
                    df.to_excel(file_path, index=False)
                else:
                    continue
                
                created_files.append(file_path)
                logger.debug(f"Query-Ergebnis exportiert: {query_name} -> {file_path}")
            
            logger.info(f"Query-Ergebnisse exportiert: {len(created_files)} Dateien")
            return created_files
            
        except Exception as e:
            logger.error(f"Fehler beim Exportieren der Query-Ergebnisse: {e}")
            raise


class SchemaExportService:
    """Service für den Export von Datenbankschemas und ER-Diagrammen"""
    
    @staticmethod
    def export_schema_json(schema_info: Dict[str, Any], output_path: str) -> str:
        """
        Exportiert Schema-Informationen als JSON
        
        Args:
            schema_info: Schema-Dictionary mit Tabellen und Beziehungen
            output_path: Ausgabepfad für die JSON-Datei
            
        Returns:
            Pfad zur erstellten JSON-Datei
        """
        try:
            schema_export = {
                **schema_info,
                "export_timestamp": pd.Timestamp.now().isoformat(),
                "table_count": len(schema_info.get("tables", {})),
                "relationship_count": len(schema_info.get("relationships", []))
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schema_export, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Schema exportiert: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fehler beim Exportieren des Schemas: {e}")
            raise
    
    @staticmethod
    def create_mermaid_er_diagram(schema_info: Dict[str, Any], output_path: str) -> str:
        """
        Erstellt ein ER-Diagramm in Mermaid-Syntax
        
        Args:
            schema_info: Schema-Dictionary mit Tabellen und Beziehungen
            output_path: Ausgabepfad für die .mmd-Datei
            
        Returns:
            Pfad zur erstellten Mermaid-Datei
        """
        try:
            mermaid_content = StringIO()
            mermaid_content.write("erDiagram\n\n")
            
            # Tabellen definieren
            tables = schema_info.get("tables", {})
            for table_name, table_info in tables.items():
                mermaid_content.write(f"    {table_name} {{\n")
                
                columns = table_info.get("columns", [])
                primary_keys = table_info.get("primary_key", [])
                
                for column in columns:
                    col_name = column.get("name", "")
                    col_type = column.get("type", "")
                    
                    # Markiere Primary Keys
                    if col_name in primary_keys:
                        col_type += " PK"
                    
                    # Nullable kennzeichnen
                    if not column.get("nullable", True):
                        col_type += " NOT NULL"
                    
                    mermaid_content.write(f"        {col_type} {col_name}\n")
                
                mermaid_content.write("    }\n\n")
            
            # Beziehungen definieren
            relationships = schema_info.get("relationships", [])
            for rel in relationships:
                source_table = rel.get("source_table", "")
                target_table = rel.get("target_table", "")
                source_column = rel.get("source_column", "")
                target_column = rel.get("target_column", "")
                
                if source_table and target_table:
                    # Mermaid Relationship Syntax
                    mermaid_content.write(
                        f"    {source_table} ||--o{{ {target_table} : "
                        f"{source_column}-{target_column}\n"
                    )
            
            # In Datei schreiben
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(mermaid_content.getvalue())
            
            logger.info(f"Mermaid ER-Diagramm erstellt: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des ER-Diagramms: {e}")
            raise
    
    @staticmethod
    def render_mermaid_to_svg(mermaid_path: str, svg_path: str) -> Optional[str]:
        """
        Rendert Mermaid-Datei zu SVG (falls mermaid-cli verfügbar)
        
        Args:
            mermaid_path: Pfad zur .mmd-Datei
            svg_path: Ausgabepfad für die SVG-Datei
            
        Returns:
            Pfad zur SVG-Datei oder None falls Rendering fehlschlägt
        """
        try:
            import subprocess
            
            # Versuche mermaid-cli zu verwenden
            result = subprocess.run([
                'mmdc', '-i', mermaid_path, '-o', svg_path, '--theme', 'default'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(svg_path):
                logger.info(f"Mermaid SVG erstellt: {svg_path}")
                return svg_path
            else:
                logger.warning(f"Mermaid CLI Fehler: {result.stderr}")
                return None
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.warning(f"Mermaid CLI nicht verfügbar oder Fehler: {e}")
            return None


class AdvancedExportService:
    """Hauptservice für erweiterte Export-Funktionen"""
    
    def __init__(self):
        self.pivot_service = PivotTableService()
        self.query_service = QueryExportService()
        self.schema_service = SchemaExportService()
    
    def export_with_advanced_options(self, 
                                   data: Dict[str, pd.DataFrame],
                                   format: str,
                                   job_id: str,
                                   export_dir: str,
                                   access_service,
                                   access_file_path: str,
                                   create_pivot_tables: bool = False,
                                   export_queries: bool = False,
                                   export_schema: bool = False) -> List[str]:
        """
        Exportiert Daten mit erweiterten Optionen
        
        Args:
            data: Tabellendaten
            format: Export-Format
            job_id: Job-ID
            export_dir: Export-Verzeichnis
            access_service: AccessService-Instanz
            access_file_path: Pfad zur Access-Datei
            create_pivot_tables: Pivot-Tabellen erstellen
            export_queries: Abfragen exportieren
            export_schema: Schema exportieren
            
        Returns:
            Liste der erstellten Dateipfade
        """
        created_files = []
        
        try:
            # Standard-Export (bestehende Logik)
            if format == 'xlsx' and create_pivot_tables:
                # Excel mit Pivot-Tabellen
                excel_path = os.path.join(export_dir, f"{job_id}_data_with_pivots.xlsx")
                self.pivot_service.create_pivot_tables(data, excel_path)
                created_files.append(excel_path)
            else:
                # Standard-Export ohne Pivot
                for table_name, df in data.items():
                    if format == 'csv':
                        file_path = os.path.join(export_dir, f"{table_name}.csv")
                        df.to_csv(file_path, index=False)
                    elif format == 'xlsx':
                        file_path = os.path.join(export_dir, f"{table_name}.xlsx")
                        df.to_excel(file_path, index=False)
                    elif format == 'json':
                        file_path = os.path.join(export_dir, f"{table_name}.json")
                        df.to_json(file_path, orient='records', indent=2)
                    else:
                        continue
                    
                    created_files.append(file_path)
            
            # Query-Export
            if export_queries:
                try:
                    queries = access_service.get_queries(access_file_path)
                    if queries:
                        # JSON mit Query-Definitionen
                        queries_json_path = os.path.join(export_dir, "queries.json")
                        self.query_service.export_queries_json(queries, queries_json_path)
                        created_files.append(queries_json_path)
                        
                        # Query-Ergebnisse (optional)
                        query_results = {}
                        for query_name in queries.keys():
                            try:
                                result_df = access_service.execute_query(access_file_path, query_name)
                                if not result_df.empty:
                                    query_results[query_name] = result_df
                            except Exception as e:
                                logger.warning(f"Abfrage {query_name} konnte nicht ausgeführt werden: {e}")
                        
                        if query_results:
                            query_files = self.query_service.export_query_results(
                                query_results, export_dir, format
                            )
                            created_files.extend(query_files)
                    
                except Exception as e:
                    logger.error(f"Query-Export fehlgeschlagen: {e}")
            
            # Schema-Export
            if export_schema:
                try:
                    schema_info = access_service.get_schema_info(access_file_path)
                    if schema_info:
                        # Schema JSON
                        schema_json_path = os.path.join(export_dir, "schema.json")
                        self.schema_service.export_schema_json(schema_info, schema_json_path)
                        created_files.append(schema_json_path)
                        
                        # ER-Diagramm (Mermaid)
                        mermaid_path = os.path.join(export_dir, "schema.mmd")
                        self.schema_service.create_mermaid_er_diagram(schema_info, mermaid_path)
                        created_files.append(mermaid_path)
                        
                        # Versuche SVG zu rendern
                        svg_path = os.path.join(export_dir, "schema.svg")
                        rendered_svg = self.schema_service.render_mermaid_to_svg(mermaid_path, svg_path)
                        if rendered_svg:
                            created_files.append(rendered_svg)
                
                except Exception as e:
                    logger.error(f"Schema-Export fehlgeschlagen: {e}")
            
            logger.info(f"Erweiterter Export abgeschlossen: {len(created_files)} Dateien erstellt")
            return created_files
            
        except Exception as e:
            logger.error(f"Fehler beim erweiterten Export: {e}")
            raise
