BEGIN;
-- Application: main
-- Model: Category
ALTER TABLE "main_category"
	ADD "modified" timestamp with time zone;

UPDATE "main_category" SET modified=now() WHERE modified is Null;

ALTER TABLE main_category ALTER COLUMN modified SET NOT NULL;

CREATE INDEX "main_category_modified_idx"
ON "main_category" ("modified");

COMMIT;
