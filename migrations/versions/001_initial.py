"""Initial migration - create all tables.

Revision ID: 001
Revises: 
Create Date: 2024-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.Enum('admin', 'doctor', 'nurse', 'staff'), nullable=False),
        sa.Column('department', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('idx_username', 'users', ['username'])
    op.create_index('idx_email', 'users', ['email'])
    
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('patient_id', sa.String(length=20), nullable=False),
        sa.Column('tc_kimlik', sa.String(length=11), nullable=True),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.Enum('E', 'K'), nullable=True),
        sa.Column('blood_type', sa.String(length=5), nullable=True),
        sa.Column('phone', sa.String(length=15), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('emergency_contact', sa.String(length=100), nullable=True),
        sa.Column('emergency_phone', sa.String(length=15), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('chronic_diseases', sa.Text(), nullable=True),
        sa.Column('created_by', mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_id'),
        sa.UniqueConstraint('tc_kimlik'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('idx_patient_id', 'patients', ['patient_id'])
    op.create_index('idx_tc_kimlik', 'patients', ['tc_kimlik'])
    op.create_index('idx_patient_name', 'patients', ['last_name', 'first_name'])
    
    # Create patient_records table
    op.create_table(
        'patient_records',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('patient_id', mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column('record_type', sa.Enum('examination', 'lab', 'imaging', 'prescription', 'spectra'), nullable=False),
        sa.Column('clinical_notes', sa.Text(), nullable=True),
        sa.Column('lab_results', sa.Text(), nullable=True),
        sa.Column('spectra_analysis', sa.JSON(), nullable=True),
        sa.Column('icd10_codes', sa.JSON(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('treatment_plan', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('doctor_notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created_by', mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('idx_record_patient', 'patient_records', ['patient_id'])
    op.create_index('idx_record_created_by', 'patient_records', ['created_by'])
    op.create_index('idx_record_created_at', 'patient_records', ['created_at'])
    op.create_index('idx_record_type', 'patient_records', ['record_type'])
    
    # Create login_attempts table
    op.create_table(
        'login_attempts',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=False),
        sa.Column('attempted_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('idx_login_username_time', 'login_attempts', ['username', 'attempted_at'])
    op.create_index('idx_login_ip_time', 'login_attempts', ['ip_address', 'attempted_at'])
    
    # Insert default admin user
    op.execute("""
        INSERT INTO users (username, email, password_hash, full_name, role, department, is_active)
        VALUES (
            'admin',
            'admin@hospital.gov.tr',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/IhK',
            'Sistem Yöneticisi',
            'admin',
            'Bilgi İşlem',
            TRUE
        )
    """)


def downgrade() -> None:
    op.drop_table('login_attempts')
    op.drop_table('patient_records')
    op.drop_table('patients')
    op.drop_table('users')
