"""Initial schema - create all tables

Revision ID: 0001
Revises: 
Create Date: 2026-01-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 启用 uuid 扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # 1. users 表
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('company', sa.String(100)),
        sa.Column('bio', sa.Text),
        sa.Column('avatar_url', sa.String(255)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_admin', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 2. api_keys 表
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key', sa.String(100), unique=True, nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 3. projects 表
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), server_default='created', nullable=False),
        sa.Column('scoring_scale', sa.String(20), server_default='1-5', nullable=False),
        sa.Column('evaluation_method', sa.String(20), server_default='auto', nullable=False),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('public', sa.Boolean, server_default='false'),
        sa.Column('evaluation_dimensions', postgresql.JSONB, server_default=sa.text(
            """'[{"name": "accuracy", "weight": 1.0, "enabled": true, "description": "评估回答的事实准确性"}, 
            {"name": "relevance", "weight": 1.0, "enabled": true, "description": "评估回答与问题的相关程度"}, 
            {"name": "completeness", "weight": 1.0, "enabled": true, "description": "评估回答信息的完整性"}, 
            {"name": "conciseness", "weight": 1.0, "enabled": false, "description": "评估回答是否简洁无冗余"}]'::jsonb"""
        )),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 4. evaluation_dimensions 表
    op.create_table(
        'evaluation_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('weight', sa.String(10), server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 5. datasets 表
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_public', sa.Boolean, server_default='false'),
        sa.Column('tags', postgresql.JSONB, server_default='[]'),
        sa.Column('dataset_metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 6. project_datasets 关联表
    op.create_table(
        'project_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('project_id', 'dataset_id', name='unique_project_dataset'),
    )

    # 7. questions 表
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('standard_answer', sa.Text, nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('difficulty', sa.String(20)),
        sa.Column('type', sa.String(50)),
        sa.Column('tags', postgresql.JSONB, server_default='[]'),
        sa.Column('question_metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_questions_dataset_id', 'questions', ['dataset_id'])
    op.create_index('idx_questions_category', 'questions', ['category'])
    op.create_index('idx_questions_difficulty', 'questions', ['difficulty'])
    op.create_index('idx_questions_created_at', 'questions', ['created_at'])

    # 8. api_configs 表
    op.create_table(
        'api_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint_url', sa.String(255), nullable=False),
        sa.Column('auth_type', sa.String(20), server_default='none', nullable=False),
        sa.Column('api_key', sa.String(255)),
        sa.Column('username', sa.String(100)),
        sa.Column('password', sa.String(255)),
        sa.Column('request_format', postgresql.JSONB),
        sa.Column('response_path', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # 9. performance_tests 表
    op.create_table(
        'performance_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True)),
        sa.Column('description', sa.Text),
        sa.Column('concurrency', sa.Integer, nullable=False),
        sa.Column('version', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), server_default='created', nullable=False),
        sa.Column('config', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('total_questions', sa.Integer, server_default='0', nullable=False),
        sa.Column('processed_questions', sa.Integer, server_default='0', nullable=False),
        sa.Column('success_questions', sa.Integer, server_default='0', nullable=False),
        sa.Column('failed_questions', sa.Integer, server_default='0', nullable=False),
        sa.Column('summary_metrics', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('rag_config', sa.String(200)),
        sa.CheckConstraint(
            "status IN ('created', 'running', 'completed', 'failed', 'terminated')",
            name='performance_tests_status_check'
        ),
    )
    op.create_index('idx_performance_tests_project_id', 'performance_tests', ['project_id'])
    op.create_index('idx_performance_status', 'performance_tests', ['status'])
    op.create_index('idx_performance_tests_version', 'performance_tests', ['version'])

    # 10. rag_answers 表
    op.create_table(
        'rag_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('answer', sa.Text, nullable=False),
        sa.Column('raw_response', postgresql.JSONB),
        sa.Column('collection_method', sa.String(20), server_default='api', nullable=False),
        sa.Column('first_response_time', sa.Numeric(10, 3)),
        sa.Column('total_response_time', sa.Numeric(10, 3)),
        sa.Column('character_count', sa.Integer),
        sa.Column('characters_per_second', sa.Numeric(10, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('version', sa.String(50)),
        sa.Column('performance_test_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('performance_tests.id', ondelete='SET NULL')),
        sa.Column('sequence_number', sa.Integer),
        sa.UniqueConstraint('question_id', 'version', name='unique_question_version'),
    )
    op.create_index('idx_rag_answers_question_id', 'rag_answers', ['question_id'])
    op.create_index('idx_rag_answers_performance_test', 'rag_answers', ['performance_test_id'])
    op.create_index('idx_rag_answers_performance', 'rag_answers', ['total_response_time', 'first_response_time'])
    op.create_index('idx_rag_answers_character_count', 'rag_answers', ['character_count'])

    # 11. accuracy_test 表
    op.create_table(
        'accuracy_test',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('evaluation_type', sa.String(20), nullable=False),
        sa.Column('scoring_method', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), server_default='created', nullable=False),
        sa.Column('dimensions', postgresql.JSONB, server_default='["accuracy"]', nullable=False),
        sa.Column('weights', postgresql.JSONB, server_default='{"accuracy": 1.0}'),
        sa.Column('model_config_test', postgresql.JSONB),
        sa.Column('prompt_template', sa.Text),
        sa.Column('version', sa.String(50)),
        sa.Column('total_questions', sa.Integer, server_default='0'),
        sa.Column('processed_questions', sa.Integer, server_default='0'),
        sa.Column('success_questions', sa.Integer, server_default='0'),
        sa.Column('failed_questions', sa.Integer, server_default='0'),
        sa.Column('batch_settings', postgresql.JSONB, server_default='{"batch_size": 10, "timeout_seconds": 300}'),
        sa.Column('results_summary', postgresql.JSONB),
        sa.Column('prompt', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint("evaluation_type IN ('ai', 'manual', 'hybrid')", name='accuracy_test_evaluation_type_check'),
        sa.CheckConstraint("scoring_method IN ('binary', 'three_scale', 'five_scale')", name='accuracy_test_scoring_method_check'),
        sa.CheckConstraint("status IN ('created', 'running', 'completed', 'failed', 'interrupted')", name='accuracy_test_status_check'),
    )
    op.create_index('idx_accuracy_test_project_id', 'accuracy_test', ['project_id'])
    op.create_index('idx_accuracy_test_dataset_id', 'accuracy_test', ['dataset_id'])
    op.create_index('idx_accuracy_test_status', 'accuracy_test', ['status'])
    op.create_index('idx_accuracy_test_version', 'accuracy_test', ['version'])

    # 12. accuracy_test_items 表
    op.create_table(
        'accuracy_test_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accuracy_test.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id'), nullable=False),
        sa.Column('rag_answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rag_answers.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('final_score', sa.Numeric),
        sa.Column('final_dimension_scores', postgresql.JSONB),
        sa.Column('final_evaluation_reason', sa.Text),
        sa.Column('final_evaluation_type', sa.String(20)),
        sa.Column('ai_score', sa.Numeric),
        sa.Column('ai_dimension_scores', postgresql.JSONB),
        sa.Column('ai_evaluation_reason', sa.Text),
        sa.Column('ai_evaluation_time', sa.DateTime(timezone=True)),
        sa.Column('ai_raw_response', postgresql.JSONB),
        sa.Column('human_score', sa.Numeric),
        sa.Column('human_dimension_scores', postgresql.JSONB),
        sa.Column('human_evaluation_reason', sa.Text),
        sa.Column('human_evaluator_id', sa.String(100)),
        sa.Column('human_evaluation_time', sa.DateTime(timezone=True)),
        sa.Column('sequence_number', sa.Integer),
        sa.Column('item_metadata', postgresql.JSONB),
        sa.UniqueConstraint('evaluation_id', 'question_id', name='unique_evaluation_question'),
        sa.CheckConstraint(
            "status IN ('pending', 'ai_completed', 'human_completed', 'both_completed', 'failed')",
            name='accuracy_test_items_status_check'
        ),
        sa.CheckConstraint("final_evaluation_type IN ('ai', 'human')", name='accuracy_test_items_final_evaluation_type_check'),
    )
    op.create_index('idx_accuracy_test_items_evaluation_id', 'accuracy_test_items', ['evaluation_id'])
    op.create_index('idx_accuracy_test_items_question_id', 'accuracy_test_items', ['question_id'])
    op.create_index('idx_accuracy_test_items_rag_answer_id', 'accuracy_test_items', ['rag_answer_id'])
    op.create_index('idx_accuracy_test_items_status', 'accuracy_test_items', ['status'])
    op.create_index('idx_accuracy_test_items_final_score', 'accuracy_test_items', ['final_score'])

    # 13. accuracy_human_assignments 表
    op.create_table(
        'accuracy_human_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accuracy_test.id', ondelete='CASCADE'), nullable=False),
        sa.Column('access_code', sa.String(20), unique=True, nullable=False),
        sa.Column('evaluator_name', sa.String(100)),
        sa.Column('evaluator_email', sa.String(255)),
        sa.Column('item_ids', postgresql.JSONB, nullable=False),
        sa.Column('total_items', sa.Integer, nullable=False),
        sa.Column('completed_items', sa.Integer, server_default='0'),
        sa.Column('status', sa.String(20), server_default='assigned'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('expiration_date', sa.DateTime(timezone=True)),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_activity_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.CheckConstraint("status IN ('assigned', 'in_progress', 'completed')", name='accuracy_human_assignments_status_check'),
    )
    op.create_index('idx_human_assignments_evaluation_id', 'accuracy_human_assignments', ['evaluation_id'])
    op.create_index('idx_human_assignments_access_code', 'accuracy_human_assignments', ['access_code'])
    op.create_index('idx_human_assignments_status', 'accuracy_human_assignments', ['status'])

    # 14. reports 表
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('public', sa.Boolean, server_default='false'),
        sa.Column('content', postgresql.JSONB),
        sa.Column('config', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_reports_project_id', 'reports', ['project_id'])
    op.create_index('idx_reports_user_id', 'reports', ['user_id'])
    op.create_index('idx_reports_report_type', 'reports', ['report_type'])
    op.create_index('idx_reports_public', 'reports', ['public'])
    op.create_index('idx_reports_created_at', 'reports', ['created_at'])

    # 15. system_settings 表
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(50), nullable=False),
        sa.Column('value', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'key', name='unique_user_setting'),
    )

    # 16. shared_projects 表
    op.create_table(
        'shared_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission', sa.String(20), server_default='read', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('project_id', 'user_id', name='unique_shared_project'),
    )

    # 17. 创建触发器函数
    op.execute("""
        CREATE OR REPLACE FUNCTION public.update_updated_at_column()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.update_datasets_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;
    """)

    # 18. 创建触发器
    op.execute("""
        CREATE TRIGGER update_reports_updated_at
        BEFORE UPDATE ON public.reports
        FOR EACH ROW
        EXECUTE PROCEDURE public.update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER trigger_update_datasets_timestamp
        BEFORE UPDATE ON public.datasets
        FOR EACH ROW
        EXECUTE PROCEDURE public.update_datasets_updated_at();
    """)

    # 19. 插入默认管理员用户 (密码: admin123)
    op.execute("""
        INSERT INTO public.users (id, email, password_hash, name, company, is_active, is_admin, created_at, updated_at)
        VALUES (
            '5bddb026-0a9d-4a87-8958-d97860566dc9',
            'admin@rag.com',
            '$2b$12$XsaDwLnTMhtvVihdFQnL8OJC6JW58x9RH47yqEThjp1IRL7Vt2Ama',
            'RAGeval',
            'RAGeval',
            true,
            true,
            now(),
            now()
        );
    """)

