BEGIN;
CREATE TABLE "main_household_users" (
    "id" serial NOT NULL PRIMARY KEY,
    "household_id" integer NOT NULL,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("household_id", "user_id")
)
;
CREATE TABLE "main_household" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL
)
;
ALTER TABLE "main_household_users" ADD CONSTRAINT "household_id_refs_id_b29d2387"
FOREIGN KEY ("household_id") REFERENCES "main_household" ("id") DEFERRABLE INITIALLY DEFERRED;

--
INSERT INTO "main_household" ("id", "name") VALUES (1, 'Bengtssons');

ALTER TABLE "main_category"
	ADD "household_id" integer;
CREATE INDEX "main_category_household_id_idx"
	ON "main_category" ("household_id");

UPDATE "main_category" SET household_id=1 WHERE household_id is Null;
ALTER TABLE main_category ALTER COLUMN household_id SET NOT NULL;

-- Model: Expense
ALTER TABLE "main_expense"
	ADD "household_id" integer;
CREATE INDEX "main_expense_household_id_idx"
	ON "main_expense" ("household_id");

UPDATE main_expense SET household_id=1 WHERE household_id is Null;
ALTER TABLE main_expense ALTER COLUMN household_id SET NOT NULL;


 COMMIT;
-- ROLLBACK;
