CREATE TABLE teachers (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    login VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('superadmin', 'teacher')),
    teacher_id BIGINT UNIQUE NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_users_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers(id)
        ON DELETE SET NULL
);

CREATE TABLE subjects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    teacher_id BIGINT NOT NULL,
    attestation_date DATE NULL,
    work_type VARCHAR(30) NOT NULL CHECK (
        work_type IN ('credit','exam','course_project')
    ),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_subject_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers(id)
);

CREATE TABLE groups (
    id BIGSERIAL PRIMARY KEY,
    group_number VARCHAR(50) UNIQUE NOT NULL,
    direction VARCHAR(255) NOT NULL,
    study_form VARCHAR(50) NOT NULL,
    course INT NOT NULL,
    semester INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE resits (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT NOT NULL,
    teacher_id BIGINT NOT NULL,
    resit_date DATE NULL,
    status VARCHAR(30) NOT NULL CHECK (
        status IN ('scheduled','completed','cancelled')
    ),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_resits_subject
        FOREIGN KEY (subject_id)
        REFERENCES subjects(id),

    CONSTRAINT fk_resits_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers(id)
);

CREATE TABLE resit_groups (
    id BIGSERIAL PRIMARY KEY,
    resit_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,

    CONSTRAINT fk_resit_groups_resit
        FOREIGN KEY (resit_id)
        REFERENCES resits(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_resit_groups_group
        FOREIGN KEY (group_id)
        REFERENCES groups(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_resit_group UNIQUE (resit_id, group_id)
);

CREATE INDEX idx_subjects_teacher_id ON subjects(teacher_id);
CREATE INDEX idx_resits_teacher_id ON resits(teacher_id);
CREATE INDEX idx_resits_subject_id ON resits(subject_id);
CREATE INDEX idx_resit_groups_resit_id ON resit_groups(resit_id);
CREATE INDEX idx_resit_groups_group_id ON resit_groups(group_id);