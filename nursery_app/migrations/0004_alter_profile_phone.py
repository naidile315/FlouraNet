from django.db import migrations

class Migration(migrations.Migration):
	"""No-op placeholder migration. The intended alteration to Profile.phone
	is implemented at the form level; keep this migration as a lightweight
	marker so the migration sequence remains sane."""

	dependencies = [
		("nursery_app", "0003_notifyrequest"),
	]

	operations = []
