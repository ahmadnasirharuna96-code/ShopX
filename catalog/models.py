from django.db import models
from django.utils.text import slugify
from common.models import TimeStampedModel
from businesses.models import Business


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        db_index=True
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    @property
    def image_url(self) -> str:
        if self.image and hasattr(self.image, "url"):
            return self.image.url
        # Stylish SVG placeholder for legacy products
        return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'><rect width='100%' height='100%' fill='%231F2937'/><text x='50%' y='45%' dominant-baseline='middle' text-anchor='middle' fill='%236B7280' font-family='sans-serif' font-size='18' font-weight='bold'>ShopX Product</text><text x='50%' y='60%' dominant-baseline='middle' text-anchor='middle' fill='%234B5563' font-family='sans-serif' font-size='14'>No Image Uploaded</text></svg>"

    def __str__(self):
        return f"{self.name} - {self.business.name} (N{self.price})"
