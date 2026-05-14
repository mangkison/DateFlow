"""Initial schema: 17 tables + indexes + triggers

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-06 00:00:00.000000

테이블 생성 순서 (FK 의존성 기준):
  1. tag_master          — 의존성 없음
  2. users               — 의존성 없음
  3. couples             — users
  4. couple_anniversaries — couples
  5. user_preferences    — users
  6. places              — PostGIS 필요
  7. visited_places      — users, places
  8. place_operating_hours — places
  9. place_reports       — places, users
 10. place_reviews       — places, users  → 트리거 등록
 11. courses             — couples, users
 12. course_places       — courses, places
 13. chat_histories      — users
 14. reservations        — users, places, courses, course_places
 15. course_feedback     — courses, users
 16. crawl_targets       — places
 17. crawl_logs          — crawl_targets
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 0. Extensions
    # =========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # =========================================================================
    # 1. tag_master
    # =========================================================================
    op.create_table(
        "tag_master",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_tag_master_code"),
        comment="atmosphere_tags 표준 코드 관리 — places.atmosphere_tags는 이 테이블의 code 값 참조",
    )

    # =========================================================================
    # 2. users
    # =========================================================================
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("kakao_id", sa.String(100), nullable=True),
        sa.Column("naver_id", sa.String(100), nullable=True),
        sa.Column("nickname", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("profile_image_url", sa.String(500), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        comment="카카오/네이버 소셜 로그인 사용자 테이블",
    )

    # =========================================================================
    # 3. couples
    # =========================================================================
    op.create_table(
        "couples",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anniversary_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_a_id"],
            ["users.id"],
            name="fk_couples_user_a",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_b_id"],
            ["users.id"],
            name="fk_couples_user_b",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_a_id", "user_b_id", name="uq_couples_pair"),
        sa.CheckConstraint(
            "user_a_id <> user_b_id", name="ck_couples_different_users"
        ),
        comment="커플 관계 테이블 — user_a_id < user_b_id 정렬은 애플리케이션 레이어 책임",
    )

    # =========================================================================
    # 4. couple_anniversaries
    # =========================================================================
    op.create_table(
        "couple_anniversaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("couple_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "reminder_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("7"),
        ),
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["couple_id"],
            ["couples.id"],
            name="fk_couple_anniversaries_couple",
            ondelete="CASCADE",
        ),
        comment="커플 기념일 — is_recurring=true 이면 매년 반복",
    )

    # =========================================================================
    # 5. user_preferences
    # =========================================================================
    op.create_table(
        "user_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preferred_atmospheres", postgresql.ARRAY(sa.String()), nullable=True
        ),
        sa.Column("budget_range_min", sa.Integer(), nullable=True),
        sa.Column("budget_range_max", sa.Integer(), nullable=True),
        sa.Column("preferred_areas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("disliked_categories", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_preferences_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
        comment="사용자 취향 설정 — 1 user : 1 preference",
    )

    # =========================================================================
    # 6. places  (PostGIS + Generated Column)
    # =========================================================================
    op.create_table(
        "places",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("road_address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        # PostGIS POINT(longitude latitude), SRID 4326 (WGS84)
        # spatial_index=False → 아래 GIST 인덱스에서 수동 생성
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sub_category", sa.String(50), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        # 장소 고유 예약 페이지 (reservations.deeplink_url과 다름)
        sa.Column("booking_page_url", sa.String(500), nullable=True),
        sa.Column("naver_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("kakao_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("google_rating", sa.Numeric(3, 1), nullable=True),
        # ── Generated Column: NULL 아닌 평점들의 평균 자동 계산 ─────────────
        sa.Column(
            "trust_score",
            sa.Numeric(3, 2),
            sa.Computed(
                """
                ROUND(
                    (COALESCE(naver_rating, 0)
                     + COALESCE(kakao_rating, 0)
                     + COALESCE(google_rating, 0))
                    / NULLIF(
                        (CASE WHEN naver_rating  IS NOT NULL THEN 1 ELSE 0 END
                         + CASE WHEN kakao_rating IS NOT NULL THEN 1 ELSE 0 END
                         + CASE WHEN google_rating IS NOT NULL THEN 1 ELSE 0 END
                        )::NUMERIC,
                        0
                    ),
                    2
                )
                """,
                persisted=True,
            ),
            nullable=True,
            comment="naver/kakao/google 평점 평균 — GENERATED ALWAYS AS STORED (읽기 전용)",
        ),
        # ── review_count: 아래 트리거(trg_place_review_count)가 자동 갱신 ───
        sa.Column(
            "review_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="place_reviews INSERT/DELETE 트리거로 자동 관리",
        ),
        sa.Column("atmosphere_tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        comment="장소 마스터 — trust_score: Generated Column, review_count: 트리거 관리",
    )

    # =========================================================================
    # 7. visited_places
    # =========================================================================
    op.create_table(
        "visited_places",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("personal_rating", sa.Numeric(2, 1), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_visited_places_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_visited_places_place",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "place_id", name="uq_visited_places_user_place"
        ),
        comment="사용자 방문 이력",
    )

    # =========================================================================
    # 8. place_operating_hours
    # =========================================================================
    op.create_table(
        "place_operating_hours",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),  # 0=월 ~ 6=일
        sa.Column("open_time", sa.Time(), nullable=True),
        sa.Column("close_time", sa.Time(), nullable=True),
        sa.Column(
            "is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_operating_hours_place",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "place_id", "day_of_week", name="uq_operating_hours_place_day"
        ),
        sa.CheckConstraint(
            "day_of_week BETWEEN 0 AND 6", name="ck_operating_hours_day_range"
        ),
        comment="장소 운영시간 — day_of_week: 0=월요일 ~ 6=일요일",
    )

    # =========================================================================
    # 9. place_reports
    # =========================================================================
    op.create_table(
        "place_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_place_reports_place",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_place_reports_user",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'resolved', 'dismissed')",
            name="ck_place_reports_status",
        ),
        comment="장소 신고 — status: pending / resolved / dismissed",
    )

    # =========================================================================
    # 10. place_reviews  (트리거 대상)
    # =========================================================================
    op.create_table(
        "place_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),  # 1 ~ 5
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "images", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),  # [{url, caption}]
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_place_reviews_place",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_place_reviews_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "place_id", "user_id", name="uq_place_reviews_place_user"
        ),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5", name="ck_place_reviews_rating_range"
        ),
        comment="장소 리뷰 — INSERT/DELETE 시 trg_place_review_count가 places.review_count 자동 갱신",
    )

    # =========================================================================
    # 11. courses
    # =========================================================================
    op.create_table(
        "courses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("couple_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("course_date", sa.Date(), nullable=False),
        sa.Column("area", sa.String(100), nullable=True),
        sa.Column("theme_tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "ai_generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["couple_id"],
            ["couples.id"],
            name="fk_courses_couple",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_courses_user",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'completed', 'cancelled')",
            name="ck_courses_status",
        ),
        comment="AI 추천 데이트 코스 — total_budget 없음, SUM(course_places.budget_allocated) 사용",
    )

    # =========================================================================
    # 12. course_places
    # =========================================================================
    op.create_table(
        "course_places",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column(
            "budget_allocated",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        # AI가 이 장소를 다른 장소로 교체했을 때 True
        sa.Column(
            "is_replaced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        # "비가 와서 실내 카페로 변경" 형태의 자연어 이유 저장
        sa.Column("replaced_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_places_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_course_places_place",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "course_id", "order_index", name="uq_course_places_order"
        ),
        comment="코스 내 장소 순서 — is_replaced/replaced_reason으로 자연어 수정 이력 추적",
    )

    # =========================================================================
    # 13. chat_histories
    # =========================================================================
    op.create_table(
        "chat_histories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),  # user / assistant / system
        sa.Column("content", sa.Text(), nullable=False),
        # {course_id, suggested_place_ids, tokens_used, model, ...}
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_histories_user",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_chat_histories_role",
        ),
        comment="챗봇 대화 이력 — session_id로 하나의 추천 세션 묶음",
    )

    # =========================================================================
    # 14. reservations
    # =========================================================================
    op.create_table(
        "reservations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("course_place_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reservation_date", sa.Date(), nullable=False),
        sa.Column("reservation_time", sa.Time(), nullable=True),
        sa.Column(
            "party_size",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("2"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        # 외부 예약 시스템이 발급한 이 예약 건 고유 딥링크 URL
        # (places.booking_page_url = 장소 고정 페이지와 다름)
        sa.Column("deeplink_url", sa.String(500), nullable=True),
        sa.Column("external_reservation_id", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_reservations_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_reservations_place",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_reservations_course",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["course_place_id"],
            ["course_places.id"],
            name="fk_reservations_course_place",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed')",
            name="ck_reservations_status",
        ),
        comment="예약 정보 — deeplink_url: 특정 예약 건 URL (≠ places.booking_page_url)",
    )

    # =========================================================================
    # 15. course_feedback
    # =========================================================================
    op.create_table(
        "course_feedback",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_rating", sa.SmallInteger(), nullable=False),  # 1 ~ 5
        # {"place_uuid_str": rating_int}
        sa.Column(
            "place_ratings", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("would_revisit", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_feedback_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_course_feedback_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "course_id", "user_id", name="uq_course_feedback_course_user"
        ),
        sa.CheckConstraint(
            "overall_rating BETWEEN 1 AND 5",
            name="ck_course_feedback_rating_range",
        ),
        comment="코스 피드백 — place_ratings: {place_uuid: rating} JSONB",
    )

    # =========================================================================
    # 16. crawl_targets
    # =========================================================================
    op.create_table(
        "crawl_targets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),  # naver / kakao / google
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column(
            "crawl_type", sa.String(50), nullable=False
        ),  # place_info / reviews / images
        sa.Column("schedule_cron", sa.String(50), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name="fk_crawl_targets_place",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "source IN ('naver', 'kakao', 'google')", name="ck_crawl_targets_source"
        ),
        comment="크롤링 대상 관리 — place_id=NULL이면 신규 장소 수집용",
    )

    # =========================================================================
    # 17. crawl_logs
    # =========================================================================
    op.create_table(
        "crawl_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("crawl_target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        # 1단계: 크롤러 원본 응답 그대로 저장 — 파싱 실패 시 재처리 기준
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="크롤링 원본 데이터 (파싱 전)",
        ),
        # 2단계: raw_data 파싱 후 정규화 — places 테이블 upsert에 사용
        sa.Column(
            "parsed_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="raw_data 파싱 결과 (정규화 후)",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "records_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(
            ["crawl_target_id"],
            ["crawl_targets.id"],
            name="fk_crawl_logs_target",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed', 'partial')",
            name="ck_crawl_logs_status",
        ),
        comment="크롤링 실행 로그 — raw_data → parsed_data 2단계 구조",
    )

    # =========================================================================
    # Indexes — B-Tree
    # =========================================================================

    # tag_master
    op.create_index("ix_tag_master_category", "tag_master", ["category"])
    op.create_index(
        "ix_tag_master_active",
        "tag_master",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # users — Partial Unique (소셜 ID는 NULL 허용이므로 partial 사용)
    op.create_index(
        "ix_users_kakao_id",
        "users",
        ["kakao_id"],
        unique=True,
        postgresql_where=sa.text("kakao_id IS NOT NULL"),
    )
    op.create_index(
        "ix_users_naver_id",
        "users",
        ["naver_id"],
        unique=True,
        postgresql_where=sa.text("naver_id IS NOT NULL"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    # 사용자 닉네임 검색용 — 삭제된 계정 제외 (id는 PK라 partial index 불필요)
    op.create_index(
        "ix_users_nickname",
        "users",
        ["nickname"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # couples
    op.create_index("ix_couples_user_a", "couples", ["user_a_id"])
    op.create_index("ix_couples_user_b", "couples", ["user_b_id"])
    op.create_index("ix_couples_status", "couples", ["status"])

    # couple_anniversaries
    op.create_index(
        "ix_couple_anniversaries_couple_id", "couple_anniversaries", ["couple_id"]
    )
    op.create_index("ix_couple_anniversaries_date", "couple_anniversaries", ["date"])

    # places — B-Tree
    op.create_index("ix_places_name", "places", ["name"])
    op.create_index("ix_places_category", "places", ["category"])
    op.create_index(
        "ix_places_trust_score",
        "places",
        [sa.text("trust_score DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_places_active",
        "places",
        ["is_active"],
        postgresql_where=sa.text("deleted_at IS NULL AND is_active = true"),
    )

    # visited_places
    op.create_index("ix_visited_places_user_id", "visited_places", ["user_id"])
    op.create_index("ix_visited_places_place_id", "visited_places", ["place_id"])
    op.create_index(
        "ix_visited_places_visited_at",
        "visited_places",
        [sa.text("visited_at DESC")],
    )

    # place_operating_hours
    op.create_index(
        "ix_operating_hours_place_id", "place_operating_hours", ["place_id"]
    )

    # place_reports
    op.create_index("ix_place_reports_place_id", "place_reports", ["place_id"])
    op.create_index("ix_place_reports_user_id", "place_reports", ["user_id"])  # FK 인덱스
    op.create_index(
        "ix_place_reports_pending",
        "place_reports",
        ["place_id"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # place_reviews
    op.create_index("ix_place_reviews_place_id", "place_reviews", ["place_id"])
    # UniqueConstraint(place_id, user_id)은 place_id 선두라 user_id 단독 조회 불가 → 별도 인덱스 필요
    op.create_index("ix_place_reviews_user_id", "place_reviews", ["user_id"])
    op.create_index(
        "ix_place_reviews_created_at",
        "place_reviews",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_place_reviews_active",
        "place_reviews",
        ["place_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # courses
    op.create_index("ix_courses_couple_id", "courses", ["couple_id"])
    op.create_index("ix_courses_user_id", "courses", ["user_id"])
    op.create_index(
        "ix_courses_course_date", "courses", [sa.text("course_date DESC")]
    )
    op.create_index("ix_courses_status", "courses", ["status"])

    # course_places
    op.create_index("ix_course_places_course_id", "course_places", ["course_id"])
    op.create_index("ix_course_places_place_id", "course_places", ["place_id"])
    op.create_index(
        "ix_course_places_replaced",
        "course_places",
        ["course_id"],
        postgresql_where=sa.text("is_replaced = true"),
    )

    # chat_histories
    op.create_index(
        "ix_chat_histories_user_session",
        "chat_histories",
        ["user_id", "session_id"],
    )
    op.create_index(
        "ix_chat_histories_created_at",
        "chat_histories",
        [sa.text("created_at DESC")],
    )

    # reservations
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_place_id", "reservations", ["place_id"])
    op.create_index("ix_reservations_course_id", "reservations", ["course_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index(
        "ix_reservations_date", "reservations", [sa.text("reservation_date DESC")]
    )
    op.create_index(
        "ix_reservations_active",
        "reservations",
        ["user_id", "reservation_date"],
        postgresql_where=sa.text("status IN ('pending', 'confirmed')"),
    )
    op.create_index(
        "ix_reservations_course_place_id", "reservations", ["course_place_id"]
    )  # FK 인덱스 — SET NULL 시 역방향 조회용

    # course_feedback
    op.create_index(
        "ix_course_feedback_course_id", "course_feedback", ["course_id"]
    )
    op.create_index("ix_course_feedback_user_id", "course_feedback", ["user_id"])
    op.create_index(
        "ix_course_feedback_rating", "course_feedback", ["overall_rating"]
    )

    # crawl_targets
    op.create_index("ix_crawl_targets_place_id", "crawl_targets", ["place_id"])
    op.create_index("ix_crawl_targets_source", "crawl_targets", ["source"])
    op.create_index(
        "ix_crawl_targets_active",
        "crawl_targets",
        ["id"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "ix_crawl_targets_last_crawled",
        "crawl_targets",
        [sa.text("last_crawled_at ASC NULLS FIRST")],
    )

    # crawl_logs
    op.create_index(
        "ix_crawl_logs_target_id", "crawl_logs", ["crawl_target_id"]
    )
    op.create_index(
        "ix_crawl_logs_started_at", "crawl_logs", [sa.text("started_at DESC")]
    )
    op.create_index("ix_crawl_logs_status", "crawl_logs", ["status"])
    op.create_index(
        "ix_crawl_logs_failed",
        "crawl_logs",
        ["crawl_target_id", sa.text("started_at DESC")],
        postgresql_where=sa.text("status IN ('failed', 'partial')"),
    )

    # =========================================================================
    # Indexes — GIST (PostGIS 공간 인덱스)
    # =========================================================================
    op.create_index(
        "ix_places_location_gist",
        "places",
        ["location"],
        postgresql_using="gist",
    )

    # =========================================================================
    # Indexes — GIN (ARRAY / JSONB 검색)
    # =========================================================================
    op.create_index(
        "ix_user_preferences_atmospheres_gin",
        "user_preferences",
        ["preferred_atmospheres"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_places_atmosphere_tags_gin",
        "places",
        ["atmosphere_tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_courses_theme_tags_gin",
        "courses",
        ["theme_tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_chat_histories_metadata_gin",
        "chat_histories",
        ["metadata"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_crawl_logs_raw_data_gin",
        "crawl_logs",
        ["raw_data"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_crawl_logs_parsed_data_gin",
        "crawl_logs",
        ["parsed_data"],
        postgresql_using="gin",
    )

    # =========================================================================
    # Functional Unique Index — couples 동시성 버그 방지
    # =========================================================================
    # UNIQUE(user_a_id, user_b_id)만으로는 (A→B)와 (B→A)가 동시에 INSERT 가능
    # LEAST/GREATEST로 순서를 정규화하여 동일 쌍을 하나로 취급
    op.create_index(
        "uq_couples_ordered_pair",
        "couples",
        [
            sa.text("LEAST(user_a_id, user_b_id)"),
            sa.text("GREATEST(user_a_id, user_b_id)"),
        ],
        unique=True,
    )

    # =========================================================================
    # Trigger: places.review_count 자동 갱신
    #
    # 처리 케이스:
    #   INSERT            → is_deleted=false 이면 +1
    #   DELETE            → is_deleted=false 였으면 -1
    #   UPDATE place_id   → 기존 place -1, 신규 place +1 (is_deleted 상태 반영)
    #   UPDATE is_deleted → false→true: -1 (소프트 삭제), true→false: +1 (복구)
    #
    # 동시성: UPDATE places ... 은 해당 row에 FOR UPDATE 락을 획득하므로
    #         같은 place에 대한 동시 카운트 갱신은 직렬화됨 (READ COMMITTED 기준)
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_update_place_review_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NOT NEW.is_deleted THEN
                    UPDATE places
                    SET review_count = review_count + 1
                    WHERE id = NEW.place_id;
                END IF;

            ELSIF TG_OP = 'DELETE' THEN
                IF NOT OLD.is_deleted THEN
                    UPDATE places
                    SET review_count = GREATEST(review_count - 1, 0)
                    WHERE id = OLD.place_id;
                END IF;

            ELSIF TG_OP = 'UPDATE' THEN
                -- Case 1: place_id 변경 (리뷰가 다른 장소로 이동, 비정상적이지만 방어)
                IF OLD.place_id IS DISTINCT FROM NEW.place_id THEN
                    IF NOT OLD.is_deleted THEN
                        UPDATE places
                        SET review_count = GREATEST(review_count - 1, 0)
                        WHERE id = OLD.place_id;
                    END IF;
                    IF NOT NEW.is_deleted THEN
                        UPDATE places
                        SET review_count = review_count + 1
                        WHERE id = NEW.place_id;
                    END IF;

                -- Case 2: is_deleted 토글 (소프트 삭제 / 복구), place_id는 동일
                ELSIF OLD.is_deleted IS DISTINCT FROM NEW.is_deleted THEN
                    IF NEW.is_deleted THEN
                        -- 소프트 삭제: 카운트 감소
                        UPDATE places
                        SET review_count = GREATEST(review_count - 1, 0)
                        WHERE id = NEW.place_id;
                    ELSE
                        -- 소프트 삭제 복구: 카운트 증가
                        UPDATE places
                        SET review_count = review_count + 1
                        WHERE id = NEW.place_id;
                    END IF;
                END IF;
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # UPDATE OF place_id, is_deleted: 이 두 컬럼이 변경될 때만 트리거 발동
    op.execute("""
        CREATE TRIGGER trg_place_review_count
        AFTER INSERT OR DELETE OR UPDATE OF place_id, is_deleted ON place_reviews
        FOR EACH ROW
        EXECUTE FUNCTION fn_update_place_review_count();
    """)


def downgrade() -> None:
    # ── 트리거 / 함수 먼저 제거 ───────────────────────────────────────────────
    op.execute(
        "DROP TRIGGER IF EXISTS trg_place_review_count ON place_reviews;"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_update_place_review_count();")

    # ── GIN / GIST / Functional 인덱스 (테이블 drop 전 명시적 제거) ──────────
    op.drop_index("ix_crawl_logs_parsed_data_gin", table_name="crawl_logs")
    op.drop_index("ix_crawl_logs_raw_data_gin", table_name="crawl_logs")
    op.drop_index("ix_chat_histories_metadata_gin", table_name="chat_histories")
    op.drop_index("ix_courses_theme_tags_gin", table_name="courses")
    op.drop_index("ix_places_atmosphere_tags_gin", table_name="places")
    op.drop_index("ix_places_location_gist", table_name="places")
    op.drop_index(
        "ix_user_preferences_atmospheres_gin", table_name="user_preferences"
    )
    op.drop_index("uq_couples_ordered_pair", table_name="couples")

    # ── 테이블 역순 삭제 (FK 의존성 역순) ─────────────────────────────────────
    op.drop_table("crawl_logs")
    op.drop_table("crawl_targets")
    op.drop_table("course_feedback")
    op.drop_table("reservations")
    op.drop_table("chat_histories")
    op.drop_table("course_places")
    op.drop_table("courses")
    op.drop_table("place_reviews")
    op.drop_table("place_reports")
    op.drop_table("place_operating_hours")
    op.drop_table("visited_places")
    op.drop_table("places")
    op.drop_table("user_preferences")
    op.drop_table("couple_anniversaries")
    op.drop_table("couples")
    op.drop_table("users")
    op.drop_table("tag_master")

    # PostGIS 익스텐션은 다른 스키마에서도 사용할 수 있으므로 DROP 하지 않음
    # op.execute("DROP EXTENSION IF EXISTS postgis CASCADE;")
