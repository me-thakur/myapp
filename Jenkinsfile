pipeline {

    agent any

    environment {
        AWS_REGION = 'us-east-1'
        AWS_ACCOUNT_ID = '361646636271'

        ECR_REPOSITORY = 'myapp'
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI = "${ECR_REGISTRY}/${ECR_REPOSITORY}:build-${BUILD_NUMBER}"

        ECS_CLUSTER = 'myapp-cluster'
        ECS_SERVICE = 'myapp-task-service'
        ECS_TASK_FAMILY = 'myapp-task'

        ECS_TASK_ROLE = 'arn:aws:iam::361646636271:role/myappECSTaskRole'
        ECS_EXECUTION_ROLE = 'arn:aws:iam::361646636271:role/ecsTaskExecutionRole'

        RDS_ENDPOINT = 'myapp-db.cexc2s0ku32a.us-east-1.rds.amazonaws.com'
        RDS_PORT = '3306'

        ALB_NAME = 'myapp-alb'
    }

    stages {

        stage('Build Docker Image') {
            steps {
                sh '''
                    echo "======================================"
                    echo "Building Docker Image"
                    echo "======================================"

                    docker build \
                        --platform linux/amd64 \
                        -t myapp:build-${BUILD_NUMBER} .
                '''
            }
        }

        stage('Run Application') {
            steps {
                sh '''
                    echo "======================================"
                    echo "Running Application"
                    echo "======================================"

                    docker rm -f myapp-jenkins-test 2>/dev/null || true

                    docker run -d \
                        --platform linux/amd64 \
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
                    echo "======================================"
                    echo "Testing Application"
                    echo "======================================"

                    docker run --rm \
                        --platform linux/amd64 \
                        --network devops-net \
                        python:3.12-slim \
                        python3 -c "import urllib.request; print(urllib.request.urlopen('http://myapp-jenkins-test:8080/health').read().decode())"
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
                        echo "======================================"
                        echo "Testing AWS Authentication"
                        echo "======================================"

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
                        echo "======================================"
                        echo "Logging in to ECR"
                        echo "======================================"

                        aws ecr get-login-password \
                            --region ${AWS_REGION} | \
                        docker login \
                            --username AWS \
                            --password-stdin ${ECR_REGISTRY}
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
                        echo "======================================"
                        echo "Pushing Image to ECR"
                        echo "======================================"

                        docker tag \
                            myapp:build-${BUILD_NUMBER} \
                            ${IMAGE_URI}

                        docker push ${IMAGE_URI}

                        echo "Image pushed:"
                        echo "${IMAGE_URI}"
                    '''
                }
            }
        }

        stage('Prepare ECS Task Definition') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "======================================"
                        echo "Preparing ECS Task Definition"
                        echo "======================================"

                        aws ecs describe-task-definition \
                            --task-definition ${ECS_TASK_FAMILY} \
                            --region ${AWS_REGION} \
                            --query 'taskDefinition' \
                            > task-definition.json

                        echo "Current task definition downloaded."

                        jq \
                            --arg IMAGE "${IMAGE_URI}" \
                            --arg TASK_ROLE "${ECS_TASK_ROLE}" \
                            --arg EXECUTION_ROLE "${ECS_EXECUTION_ROLE}" \
                            --arg DB_HOST "${RDS_ENDPOINT}" \
                            --arg DB_PORT "${RDS_PORT}" \
                            '
                            .containerDefinitions |=
                            map(
                                if .name == "myapp"
                                then
                                    .image = $IMAGE
                                    |
                                    .environment = [
                                        {
                                            "name": "DB_HOST",
                                            "value": $DB_HOST
                                        },
                                        {
                                            "name": "DB_PORT",
                                            "value": $DB_PORT
                                        }
                                    ]
                                else .
                                end
                            )
                            |
                            .taskRoleArn = $TASK_ROLE
                            |
                            .executionRoleArn = $EXECUTION_ROLE
                            |
                            del(
                                .taskDefinitionArn,
                                .revision,
                                .status,
                                .requiresAttributes,
                                .compatibilities,
                                .registeredAt,
                                .registeredBy
                            )
                            ' task-definition.json > new-task-definition.json

                        echo "New task definition prepared."

                        echo "--------------------------------------"
                        echo "Image:"
                        jq -r '.containerDefinitions[] | select(.name == "myapp") | .image' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Task Role:"
                        jq -r '.taskRoleArn' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Execution Role:"
                        jq -r '.executionRoleArn' new-task-definition.json

                        echo "--------------------------------------"
                        echo "Database Configuration:"
                        jq -r '.containerDefinitions[] | select(.name == "myapp") | .environment' new-task-definition.json
                    '''
                }
            }
        }

        stage('Register ECS Task Definition') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "======================================"
                        echo "Registering ECS Task Definition"
                        echo "======================================"

                        NEW_TASK_DEFINITION=$(aws ecs register-task-definition \
                            --cli-input-json file://new-task-definition.json \
                            --region ${AWS_REGION} \
                            --query 'taskDefinition.taskDefinitionArn' \
                            --output text)

                        echo "Registered:"
                        echo "${NEW_TASK_DEFINITION}"

                        echo "${NEW_TASK_DEFINITION}" > new-task-definition-arn.txt
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
                        echo "======================================"
                        echo "Deploying to ECS"
                        echo "======================================"

                        NEW_TASK_DEFINITION=$(cat new-task-definition-arn.txt)

                        aws ecs update-service \
                            --cluster ${ECS_CLUSTER} \
                            --service ${ECS_SERVICE} \
                            --task-definition ${NEW_TASK_DEFINITION} \
                            --enable-execute-command \
                            --region ${AWS_REGION}

                        echo "ECS deployment triggered."
                        echo "Task Definition:"
                        echo "${NEW_TASK_DEFINITION}"
                    '''
                }
            }
        }

        stage('Wait for ECS Deployment') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "======================================"
                        echo "Waiting for ECS Deployment"
                        echo "======================================"

                        aws ecs wait services-stable \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION}

                        echo "ECS service is stable."
                    '''
                }
            }
        }

        stage('Verify ECS Deployment') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "======================================"
                        echo "Verifying ECS Deployment"
                        echo "======================================"

                        aws ecs describe-services \
                            --cluster ${ECS_CLUSTER} \
                            --services ${ECS_SERVICE} \
                            --region ${AWS_REGION} \
                            --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDefinition:taskDefinition,ExecuteCommand:enableExecuteCommand}' \
                            --output table
                    '''
                }
            }
        }

        stage('Verify Application through ALB') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'jenkins-ecr-aws',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        echo "======================================"
                        echo "Verifying Application through ALB"
                        echo "======================================"

                        ALB_DNS=$(aws elbv2 describe-load-balancers \
                            --names ${ALB_NAME} \
                            --region ${AWS_REGION} \
                            --query 'LoadBalancers[0].DNSName' \
                            --output text)

                        echo "ALB DNS:"
                        echo "${ALB_DNS}"

                        echo "--------------------------------------"
                        echo "Testing /health"
                        echo "--------------------------------------"

                        for i in $(seq 1 12); do

                            RESPONSE=$(curl -s \
                                --max-time 5 \
                                "http://${ALB_DNS}/health" || true)

                            echo "Attempt ${i}: ${RESPONSE}"

                            if [ "${RESPONSE}" = "OK" ]; then
                                echo "Application health check PASSED."
                                exit 0
                            fi

                            echo "Application not ready yet. Waiting 10 seconds..."
                            sleep 10

                        done

                        echo "Application health check FAILED."
                        exit 1
                    '''
                }
            }
        }
    }

    post {

        success {
            echo "======================================"
            echo "PIPELINE SUCCESS"
            echo "======================================"
            echo "Application successfully deployed to ECS."
            echo "ALB health check passed."
        }

        failure {
            echo "======================================"
            echo "PIPELINE FAILED"
            echo "======================================"
            echo "Check the failed stage above."
        }

        always {
            sh '''
                docker rm -f myapp-jenkins-test 2>/dev/null || true
            '''
        }
    }
}