from django.db import models


class Account(models.Model):
    name = models.CharField(max_length=100)


class Movement(models.Model):
    voucher = models.CharField(max_length=20)
    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
