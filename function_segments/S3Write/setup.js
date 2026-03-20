exports.setup = async () => {
  // START SETUP
  const AWS = require(root + "/aws-sdk");
  const S3 = new AWS.S3();

  const params = {
    Bucket: "long.ma.s3write.{{.BucketName}}",
    CreateBucketConfiguration: {
      LocationConstraint: "us-west-2"
    }
  };
  await S3.createBucket(params).promise();
  console.log(`successfully created S3 Bucket ${params.Bucket}`);
  // END SETUP
}