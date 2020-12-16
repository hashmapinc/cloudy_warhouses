import pandas as pd
import logging
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from snowflake.connector.pandas_tools import write_pandas
from snowflake.connector.pandas_tools import pd_writer
from cloudy_warehouses.snowflake_objects.snowflake_object import SnowflakeObject


@pd.api.extensions.register_dataframe_accessor("cloudy_warehouses")
class SnowflakeWriter(SnowflakeObject):
    """Writer Object: contains write_snowflake and create_snowflake methods."""

    # True when write_snowflake successfully runs
    write_success = False
    # cursor executes this in create_snowflake method
    sql_statement = str
    # used in as columns in create_snowflake method
    table_columns = []
    # SQL Alchemy Engine
    engine = None

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def write_snowflake(self, database: str, schema: str, table: str, sf_username: str = None, sf_password: str = None,
                        sf_account: str = None, warehouse: str = None, role: str = None):
        """Uploads data from a pandas dataframe to an existing Snowflake table."""

        try:
            # initialize Snowflake connection and configure credentials
            self.initialize_snowflake(
                             database=database,
                             schema=schema,
                             sf_username=sf_username,
                             sf_password=sf_password,
                             sf_account=sf_account
                             )

            # create SQL Alchemy engine
            if warehouse and not role:
                self.engine = create_engine(URL(
                    user=self.sf_credentials['user'],
                    password=self.sf_credentials['pass'],
                    account=self.sf_credentials['acct'],
                    database=database,
                    schema=schema,
                    warehouse=warehouse
                ))

            elif role and not warehouse:
                self.engine = create_engine(URL(
                    user=self.sf_credentials['user'],
                    password=self.sf_credentials['pass'],
                    account=self.sf_credentials['acct'],
                    database=database,
                    schema=schema,
                    role=role,
                ))

            elif role and warehouse:
                self.engine = create_engine(URL(
                    user=self.sf_credentials['user'],
                    password=self.sf_credentials['pass'],
                    account=self.sf_credentials['acct'],
                    database=database,
                    schema=schema,
                    warehouse=warehouse,
                    role=role
                ))

            else:
                self.engine = create_engine(URL(
                    user=self.sf_credentials['user'],
                    password=self.sf_credentials['pass'],
                    account=self.sf_credentials['acct'],
                    database=database,
                    schema=schema
                ))

            # calls method to write data in a pandas dataframe to an existing Snowflake table
            self.df.to_sql(table, con=self.engine, index=False, if_exists='append', method=pd_writer)

            self.write_success = True

        # catch and log error
        except Exception as e:
            self.log_message = e
            self._logger.error(self.log_message)
            return False

        finally:
            # close connection
            if self.connection:
                self.connection.close()
                self.engine.dispose()

        if self.write_success:
            self.log_message = f"Successfully wrote to the {table} Snowflake table"
            self._logger.error(self.log_message)
            return True

    def create_snowflake(self, database: str, schema: str, table: str, sf_username: str = None, sf_password: str = None,
                         sf_account: str = None):
        """method that creates a Snowflake table and writes pandas dataframe to table."""

        try:
            # initialize Snowflake connection and configure credentials
            self.initialize_snowflake(
                             database=database,
                             schema=schema,
                             sf_username=sf_username,
                             sf_password=sf_password,
                             sf_account=sf_account
                             )
            # for loop to generate a string of columns for sql statement
            for key in self.df.keys():
                if key != self.df.keys()[-1]:
                    self.table_columns.append(key + ' variant, ')
                else:
                    self.table_columns.append(key + ' variant')

            # sql statement to be executed in Snowflake
            self.sql_statement = f"CREATE OR REPLACE TABLE {database}.{schema}.{table}({''.join(self.table_columns)})"

            # execute sql statement
            self.cursor = self.connection.cursor()
            self.cursor.execute(self.sql_statement)

            # calls method to write data in a pandas dataframe to an existing Snowflake table
            success, nchunks, nrows, _ = write_pandas(
                conn=self.connection,
                df=self.df,
                table_name=table
            )

        # catch and log error
        except Exception as e:
            self.log_message = e
            self._logger.error(self.log_message)
            return False

        finally:
            # close connection and cursor
            if self.connection:
                self.connection.close()
            if self.cursor:
                self.cursor.close()

        self.log_message = f"Successfully created and wrote to the {table} Snowflake table"
        self._logger.error(self.log_message)
        return True
