"""
UCanAccess service for reading Microsoft Access databases on Linux
"""
import jaydebeapi
import jpype
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger
from app.models import TableInfo

logger = get_logger(__name__)


class UCanAccessError(Exception):
    """Custom exception for UCanAccess operations"""
    pass


class UCanAccessService:
    """Service for accessing Microsoft Access databases using UCanAccess"""
    
    def __init__(self):
        self.driver_class = "net.ucanaccess.jdbc.UcanaccessDriver"
        self.connection = None
        self._jvm_started = False
        
    def _start_jvm(self):
        """Start the JVM if not already started"""
        if not self._jvm_started and not jpype.isJVMStarted():
            try:
                # Build classpath
                classpath = self._build_classpath()
                
                # Start JVM with classpath
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    f"-Djava.class.path={classpath}",
                    "-Xmx1024m"  # Increase heap size for large databases
                )
                
                self._jvm_started = True
                logger.info("JVM started successfully", classpath=classpath)
                
            except Exception as e:
                logger.error("Failed to start JVM", error=str(e))
                raise UCanAccessError(f"Could not start JVM: {str(e)}")
    
    def _build_classpath(self) -> str:
        """Build Java classpath for UCanAccess"""
        ucanaccess_dir = Path(settings.ucanaccess_path)
        
        if not ucanaccess_dir.exists():
            raise UCanAccessError(f"UCanAccess directory not found: {ucanaccess_dir}")
        
        # Required JAR files
        jar_files = [
            "ucanaccess-5.0.1.jar",
            "lib/commons-lang3-3.8.1.jar",
            "lib/commons-logging-1.2.jar", 
            "lib/hsqldb-2.5.0.jar",
            "lib/jackcess-4.0.2.jar"
        ]
        
        classpath_parts = []
        for jar_file in jar_files:
            jar_path = ucanaccess_dir / jar_file
            if jar_path.exists():
                classpath_parts.append(str(jar_path))
            else:
                logger.warning("JAR file not found", jar_file=jar_file, path=str(jar_path))
        
        if not classpath_parts:
            raise UCanAccessError("No UCanAccess JAR files found")
        
        return os.pathsep.join(classpath_parts)
    
    def connect(self, db_path: str) -> None:
        """Connect to an Access database"""
        self._start_jvm()
        
        try:
            # Build JDBC URL
            db_path_absolute = Path(db_path).resolve()
            if not db_path_absolute.exists():
                raise UCanAccessError(f"Database file not found: {db_path_absolute}")
            
            # UCanAccess JDBC URL format
            jdbc_url = f"jdbc:ucanaccess://{db_path_absolute}"
            
            # Additional connection properties for better compatibility
            properties = {
                "charSet": "UTF-8",
                "showSchema": "true"
            }
            
            # Create connection
            self.connection = jaydebeapi.connect(
                self.driver_class,
                jdbc_url,
                properties
            )
            
            logger.info("Connected to Access database", 
                       db_path=str(db_path_absolute),
                       jdbc_url=jdbc_url)
            
        except Exception as e:
            logger.error("Failed to connect to database", 
                        db_path=db_path,
                        error=str(e))
            raise UCanAccessError(f"Connection failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("Disconnected from Access database")
            except Exception as e:
                logger.warning("Error during disconnect", error=str(e))
    
    def list_tables(self) -> List[TableInfo]:
        """Get list of all tables in the database"""
        if not self.connection:
            raise UCanAccessError("Not connected to database")
        
        try:
            cursor = self.connection.cursor()
            
            # Get table metadata
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE IN ('TABLE', 'VIEW')
                ORDER BY TABLE_NAME
            """)
            
            tables = []
            for row in cursor.fetchall():
                table_name = row[0]
                table_type = row[1]
                
                try:
                    # Get table info (column count and row count)
                    table_info = self._get_table_info(table_name)
                    tables.append(table_info)
                    
                except Exception as e:
                    logger.warning("Could not get info for table", 
                                 table_name=table_name,
                                 error=str(e))
                    # Add table with basic info even if we can't get details
                    tables.append(TableInfo(
                        name=table_name,
                        row_count=0,
                        column_count=0,
                        columns=[]
                    ))
            
            cursor.close()
            
            logger.info("Retrieved table list", table_count=len(tables))
            return tables
            
        except Exception as e:
            logger.error("Failed to list tables", error=str(e))
            raise UCanAccessError(f"Could not list tables: {str(e)}")
    
    def _get_table_info(self, table_name: str) -> TableInfo:
        """Get detailed information about a specific table"""
        cursor = self.connection.cursor()
        
        try:
            # Get column information
            cursor.execute(f"SELECT * FROM [{table_name}] WHERE 1=0")  # Get structure only
            columns = [desc[0] for desc in cursor.description]
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            row_count = cursor.fetchone()[0]
            
            return TableInfo(
                name=table_name,
                row_count=row_count,
                column_count=len(columns),
                columns=columns
            )
            
        finally:
            cursor.close()
    
    def read_table(self, table_name: str, chunk_size: Optional[int] = None) -> pd.DataFrame:
        """Read data from a table into a pandas DataFrame"""
        if not self.connection:
            raise UCanAccessError("Not connected to database")
        
        try:
            query = f"SELECT * FROM [{table_name}]"
            
            if chunk_size:
                # For large tables, we might want to implement chunked reading
                # For now, read all data at once
                pass
            
            df = pd.read_sql(query, self.connection)
            
            logger.info("Read table data", 
                       table_name=table_name,
                       rows=len(df),
                       columns=len(df.columns))
            
            return df
            
        except Exception as e:
            logger.error("Failed to read table", 
                        table_name=table_name,
                        error=str(e))
            raise UCanAccessError(f"Could not read table {table_name}: {str(e)}")
    
    def read_table_chunked(self, table_name: str, chunk_size: int = 1000):
        """Generator that yields table data in chunks"""
        if not self.connection:
            raise UCanAccessError("Not connected to database")
        
        try:
            # First get total row count
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            total_rows = cursor.fetchone()[0]
            cursor.close()
            
            # Read data in chunks
            offset = 0
            while offset < total_rows:
                query = f"""
                    SELECT * FROM [{table_name}]
                    ORDER BY (SELECT NULL)
                    OFFSET {offset} ROWS
                    FETCH NEXT {chunk_size} ROWS ONLY
                """
                
                try:
                    chunk_df = pd.read_sql(query, self.connection)
                    if chunk_df.empty:
                        break
                    
                    yield chunk_df
                    offset += chunk_size
                    
                except Exception as e:
                    # Some Access databases might not support OFFSET/FETCH
                    # Fall back to reading all data at once
                    logger.warning("Chunked reading not supported, reading full table", 
                                 table_name=table_name,
                                 error=str(e))
                    
                    full_df = pd.read_sql(f"SELECT * FROM [{table_name}]", self.connection)
                    for i in range(0, len(full_df), chunk_size):
                        yield full_df.iloc[i:i+chunk_size]
                    break
            
        except Exception as e:
            logger.error("Failed to read table in chunks", 
                        table_name=table_name,
                        error=str(e))
            raise UCanAccessError(f"Could not read table {table_name} in chunks: {str(e)}")
    
    def test_connection(self, db_path: str) -> Tuple[bool, Optional[str]]:
        """Test if we can connect to a database file"""
        try:
            self.connect(db_path)
            
            # Try to list tables as a connection test
            tables = self.list_tables()
            
            self.disconnect()
            
            return True, f"Successfully connected. Found {len(tables)} tables."
            
        except Exception as e:
            return False, str(e)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Global service instance
ucanaccess_service = UCanAccessService()
