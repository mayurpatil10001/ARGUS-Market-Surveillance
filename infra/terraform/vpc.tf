# VPC — 3 public + 3 private subnets across 3 AZs in ap-south-1
# Public subnets : EC2, ALB
# Private subnets: RDS, ElastiCache, MSK

resource "aws_vpc" "argus" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "argus-vpc" }
}

# Internet gateway
resource "aws_internet_gateway" "argus" {
  vpc_id = aws_vpc.argus.id
  tags   = { Name = "argus-igw" }
}

data "aws_availability_zones" "available" { state = "available" }

# 3 public subnets (ap-south-1a, 1b, 1c)
resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.argus.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "argus-public-${count.index}" }
}

# 3 private subnets
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.argus.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = { Name = "argus-private-${count.index}" }
}

# NAT gateway (single, in first public subnet) for private-subnet outbound
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "argus-nat-eip" }
}
resource "aws_nat_gateway" "argus" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.argus]
  tags          = { Name = "argus-nat" }
}

# Public route table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.argus.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.argus.id
  }
  tags = { Name = "argus-public-rt" }
}
resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route table (egress via NAT)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.argus.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.argus.id
  }
  tags = { Name = "argus-private-rt" }
}
resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
