pipeline {

    agent any

    stages {

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build --platform linux/amd64 \
                        -t myapp:build-${BUILD_NUMBER} .
                '''
            }
        }

        stage('Run Application') {
            steps {
                sh '''
                    docker rm -f myapp-jenkins-test 2>/dev/null || true

                    docker run -d \
                        --name myapp-jenkins-test \
                        --network devops-net \
                        -p 8082:8080 \
                        myapp:build-${BUILD_NUMBER}
                '''
            }
        }

        stage('Test Application') {
            steps {
                sh '''
                    docker run --rm \
                        --network devops-net \
                        python:3.12-slim \
                        python3 -c "import urllib.request; print(urllib.request.urlopen('http://myapp-jenkins-test:8080').read().decode())"
                '''
            }
        }

        stage('Test AWS Authentication') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        aws sts get-caller-identity
                    '''
                }
            }
        }

        stage('Login to ECR') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        aws ecr get-login-password --region us-east-1 | \
                        docker login \
                            --username AWS \
                            --password-stdin \
                            361646636271.dkr.ecr.us-east-1.amazonaws.com
                    '''
                }
            }
        }

        stage('Push Image to ECR') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        docker tag \
                            myapp:build-${BUILD_NUMBER} \
                            361646636271.dkr.ecr.us-east-1.amazonaws.com/myapp:build-${BUILD_NUMBER}

                        docker push \
                            361646636271.dkr.ecr.us-east-1.amazonaws.com/myapp:build-${BUILD_NUMBER}
                    '''
                }
            }
        }

        stage('Deploy to ECS') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "Deploying build-${BUILD_NUMBER} to ECS..."

                        IMAGE_URI="361646636271.dkr.ecr.us-east-1.amazonaws.com/myapp:build-${BUILD_NUMBER}"

                        echo "Image: ${IMAGE_URI}"

                        aws ecs describe-task-definition \
                            --task-definition myapp-task \
                            --region us-east-1 \
                            --query 'taskDefinition' \
                            > task-definition.json

                        python3 - <<PY
import json

with open("task-definition.json") as f:
    task = json.load(f)

image = "361646636271.dkr.ecr.us-east-1.amazonaws.com/myapp:build-${BUILD_NUMBER}"

for container in task["containerDefinitions"]:
    if container["name"] == "myapp":
        container["image"] = image

fields = [
    "family",
    "taskRoleArn",
    "executionRoleArn",
    "networkMode",
    "containerDefinitions",
    "volumes",
    "placementConstraints",
    "requiresCompatibilities",
    "cpu",
    "memory",
    "runtimePlatform"
]

new_task = {
    key: task[key]
    for key in fields
    if key in task
}

with open("new-task-definition.json", "w") as f:
    json.dump(new_task, f)

print("New task definition prepared")
print("Image:", image)
PY

                        aws ecs register-task-definition \
                            --cli-input-json file://new-task-definition.json \
                            --region us-east-1

                        aws ecs update-service \
                            --cluster myapp-cluster \
                            --service myapp-task-service \
                            --task-definition myapp-task \
                            --region us-east-1

                        echo "ECS deployment triggered successfully."
                    '''
                }
            }
        }
    }
}
