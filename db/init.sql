IF DB_ID(N'$(DatabaseName)') IS NULL CREATE DATABASE [$(DatabaseName)];
GO
IF SUSER_ID(N'$(DatabaseName)') IS NULL
BEGIN
    DECLARE @password NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), 0x$(PasswordHex));
    IF DATALENGTH(@password) > 256 THROW 50000, 'SQL login password exceeds 128 characters', 1;
    DECLARE @sql NVARCHAR(MAX) = N'CREATE LOGIN [$(DatabaseName)] WITH PASSWORD = '
        + QUOTENAME(@password, '''');
    EXEC (@sql);
END;
GO
USE [$(DatabaseName)];
GO
IF USER_ID(N'$(DatabaseName)') IS NULL
    CREATE USER [$(DatabaseName)] FOR LOGIN [$(DatabaseName)] WITH DEFAULT_SCHEMA = dbo;
IF IS_ROLEMEMBER('db_owner', '$(DatabaseName)') = 0
    ALTER ROLE db_owner ADD MEMBER [$(DatabaseName)];
